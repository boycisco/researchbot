import logging
import threading
import time
import json
import utils
from core.database import *
from stages import search
from stages import fetch
from stages import verify
from stages import claims
from stages import compare
from stages import writer
from stages import checker
from core import package as pkg
from ai import prompts
from core import providers
from core import confidence

logger = utils.logger

# Concurrency control (process-wide semaphores)
research_semaphore = threading.Semaphore(5)  # max concurrent research jobs
fetch_semaphore = threading.Semaphore(5)     # max concurrent fetches

def run_research(research_id, progress_callback=None, profile=None):
    """Main orchestration function for a research job. Runs in a separate thread."""
    if profile is None:
        from request import DEPTH_PROFILES
        profile = DEPTH_PROFILES["standard"]

    with research_semaphore:
        try:
            logger.info(f"Starting research {research_id}")
            research = get_research(research_id)
            if not research:
                logger.error(f"Research {research_id} not found")
                return
            user_id = research['user_id']
            topic = research['topic']

            def send_progress(stage):
                if progress_callback:
                    progress_callback(research_id, stage)

            def check_cancelled(stage_name):
                """Return True if cancellation was requested; mark and signal if so."""
                if is_cancel_requested(research_id):
                    logger.info(f"Research {research_id} cancelled at stage '{stage_name}'")
                    update_research_status(research_id, status='cancelled', stage=stage_name)
                    send_progress('cancelled')
                    return True
                return False

            # Stage 1: Analysis
            send_progress('analysis')
            update_research_status(research_id, status='analyzing', stage='analysis')
            analysis_result = providers.generate_json(prompts.analysis_prompt(topic))
            if not analysis_result['success']:
                update_research_status(research_id, status='failed', stage='analysis', error=analysis_result.get('error'))
                send_progress('failed')
                return
            analysis = analysis_result['data']
            update_research_status(research_id, intent=analysis.get('intent', ''))
            logger.info(f"Analysis done: {analysis.get('main_topic')}")

            if check_cancelled('analysis'):
                return

            # Stage 2: Query generation
            send_progress('query_generation')
            update_research_status(research_id, status='planning', stage='query_generation')
            queries = search.generate_queries(
                json.dumps(analysis),
                max_queries=profile['max_queries'],
            )
            if queries is None or len(queries) == 0:
                update_research_status(research_id, status='failed', stage='query_generation', error='No queries generated')
                send_progress('failed')
                return
            insert_queries(research_id, queries)
            query_rows = get_queries(research_id)
            if not query_rows:
                update_research_status(research_id, status='failed', stage='query_generation', error='Failed to retrieve queries')
                send_progress('failed')
                return
            logger.info(f"Generated {len(query_rows)} queries")

            # Stage 3: Search
            send_progress('search')
            update_research_status(research_id, status='searching', stage='search')
            all_sources = []
            for q in query_rows:
                if check_cancelled('search'):
                    return
                results = providers.search_web(
                    q['query'],
                    max_results=profile['max_search_results_per_query'],
                )
                for result in results:
                    canonical = result.get('canonical_url') or result.get('url')
                    if not any(
                        (s.get('canonical_url') or s.get('url')) == canonical
                        for s in all_sources
                    ):
                        all_sources.append(result)
                        source_id = insert_source(research_id, q['id'], result)
                        result['id'] = source_id
                time.sleep(1)
            if not all_sources:
                update_research_status(research_id, status='failed', stage='search', error='No sources found')
                send_progress('failed')
                return
            logger.info(f"Found {len(all_sources)} sources")

            # Stage 4: Fetch sources (bounded concurrency)
            send_progress('fetching')
            update_research_status(research_id, status='fetching', stage='fetching')
            all_sources = all_sources[:profile['max_sources_to_fetch']]
            for source in all_sources:
                if check_cancelled('fetching'):
                    return
                with fetch_semaphore:
                    fetch_result = fetch.fetch_source(source['url'])
                if fetch_result['success']:
                    source['content'] = fetch_result['content']
                    source['word_count'] = fetch_result['word_count']
                    source['title'] = fetch_result.get('title') or source.get('title')
                    source['published_at'] = fetch_result.get('published_at')
                    update_source_fetch(source['id'], fetch_result)
                else:
                    update_source_fetch(source['id'], {
                        'status': fetch_result.get('status', 'failed'),
                        'http_status': fetch_result.get('http_status')
                    })

            # Limit to top 5 sources with content
            sources_with_content = [
                s for s in all_sources
                if 'content' in s and s['content']
            ][:profile['max_sources_to_verify']]
            if not sources_with_content:
                update_research_status(research_id, status='failed', stage='fetching', error='No sources fetched successfully')
                send_progress('failed')
                return
            logger.info(
                f"Fetched content from {len(sources_with_content)} sources "
                f"(depth={profile.get('max_sources_to_verify')})"
            )

            if check_cancelled('pre_verification'):
                return

            # Stage 5: Verify sources (batch)
            send_progress('verification')
            update_research_status(research_id, status='verifying', stage='verification')
            verified_results = verify.verify_sources(sources_with_content, topic)
            verified_count = 0
            for i, source in enumerate(sources_with_content):
                if i >= len(verified_results):
                    break
                verify_result = verified_results[i]
                if verify_result.get('status') == 'verified':
                    update_source_verification(source['id'], verify_result)
                    source.update({
                        'verification_status': 'verified',
                        'relevance_score': verify_result.get('relevance_score'),
                        'quality_score': verify_result.get('quality_score'),
                        'evidence_score': verify_result.get('evidence_score'),
                        'recency_score': verify_result.get('recency_score'),
                        'bias_score': verify_result.get('bias_score'),
                        'completeness_score': verify_result.get('completeness_score'),
                        'source_type': verify_result.get('source_type'),
                        'is_primary': verify_result.get('is_primary')
                    })
                    verified_count += 1
                else:
                    update_source_verification(source['id'], {'status': 'rejected', 'reason': verify_result.get('reason', '')})
            if verified_count == 0:
                update_research_status(research_id, status='failed', stage='verification', error='No relevant sources')
                send_progress('failed')
                return
            verified_sources = [s for s in sources_with_content if s.get('verification_status') == 'verified']
            logger.info(f"Verified {verified_count} sources")

            if check_cancelled('pre_claim_extraction'):
                return

            # Stage 6: Extract claims (batch)
            send_progress('claim_extraction')
            update_research_status(research_id, status='extracting', stage='claim_extraction')
            extracted_claims = claims.extract_claims_batch(
                [{'source_id': s['id'], 'content': s['content']} for s in verified_sources],
                topic
            )
            if not extracted_claims:
                update_research_status(research_id, status='failed', stage='claim_extraction', error='No claims extracted')
                send_progress('failed')
                return
            for claim_data in extracted_claims:
                claim_id = insert_claim(research_id, claim_data['source_id'], claim_data)
                claim_data['id'] = claim_id
                claim_data['source_url'] = next((s['url'] for s in verified_sources if s['id'] == claim_data['source_id']), '')
            all_claims = extracted_claims
            logger.info(f"Extracted {len(all_claims)} claims")

            # Stage 7: Compare claims
            send_progress('comparison')
            update_research_status(research_id, status='comparing', stage='comparison')
            claims_rows = get_claims(research_id)
            candidate_pairs = compare.find_candidate_pairs(
                claims_rows,
                max_pairs=profile['max_claim_pairs'],
            )
            for claim_a, claim_b, sim in candidate_pairs:
                if check_cancelled('comparison'):
                    return
                rel_result = compare.compare_claims(claim_a, claim_b)
                if rel_result:
                    insert_relationship(research_id, claim_a['id'], claim_b['id'], rel_result)
            relationships_rows = get_relationships(research_id)
            classified = compare.detect_contradictions(claims_rows, relationships_rows)
            logger.info(
                f"Compared claims: {len(relationships_rows)} relationships "
                f"({len(classified['true_contradictions'])} true contradictions, "
                f"{len(classified['different_contexts'])} different context, "
                f"{len(classified['qualifiers'])} qualifiers)"
            )

            # Stage 7b: Deterministic confidence scoring
            send_progress('confidence')
            update_research_status(research_id, status='scoring', stage='confidence')
            sources_by_id = {s['id']: s for s in verified_sources}
            for c in claims_rows:
                conf = confidence.compute_confidence(c, claims_rows, relationships_rows, sources_by_id)
                update_claim_confidence(c['id'], conf['score'], conf['level'], conf['explanation'])
            # Refresh from DB so packaging sees the new fields
            claims_rows = get_claims(research_id)
            logger.info("Computed confidence for all claims")

            # Stage 8: Build package
            send_progress('packaging')
            update_research_status(research_id, status='packaging', stage='packaging')
            package_content = pkg.build_package(
                research,
                verified_sources,
                claims_rows,
                relationships_rows,
                query_rows,
                min_confidence_for_key_findings=profile['min_confidence_for_key_findings'],
            )
            store_package(research_id, package_content)
            logger.info("Package built")

            if check_cancelled('pre_writing'):
                return

            # Stage 9: Write answer
            send_progress('writing')
            update_research_status(research_id, status='writing', stage='writing')
            try:
                _pkg = json.loads(package_content)
                logger.info(
                    f"Package contains {len(_pkg.get('sources', []))} sources, "
                    f"{len(_pkg.get('claims', []))} claims"
                )
            except Exception:
                pass
            answer_text = writer.write_answer(package_content, topic, analysis.get('intent', ''))
            if not answer_text:
                update_research_status(research_id, status='failed', stage='writing', error='Answer generation failed')
                send_progress('failed')
                return
            store_answer(research_id, answer_text, 'unverified')

            if check_cancelled('pre_fact_checking'):
                return

            # Stage 10: Fact check and revision loop
            send_progress('fact_checking')
            update_research_status(research_id, status='checking', stage='fact_checking')
            max_revisions = profile['max_revisions']
            final_verification_status = None

            for attempt in range(max_revisions + 1):
                if check_cancelled('fact_checking'):
                    return
                check_result = checker.check_answer(answer_text, package_content)

                if check_result['status'] == 'verification_error':
                    update_research_status(
                        research_id,
                        status='failed',
                        stage='fact_checking',
                        error='Fact checker error',
                    )
                    store_answer(research_id, answer_text, 'verification_error')
                    send_progress('failed')
                    return

                if check_result['status'] == 'passed':
                    logger.info(
                        f"Fact check passed: {check_result['sentences_checked']} sentence(s) checked, "
                        f"0 problematic"
                    )
                    final_verification_status = 'verified'
                    break

                logger.info(
                    f"Fact check returned status={check_result['status']}, "
                    f"checked={check_result['sentences_checked']}, "
                    f"problematic={len(check_result['problematic'])}"
                )

                # Failed — try to revise
                if attempt < max_revisions:
                    logger.info(
                        f"Fact check failed (attempt {attempt+1}); "
                        f"{len(check_result['problematic'])} problematic sentence(s)"
                    )
                    revision_prompt = prompts.revision_prompt(
                        package_content,
                        topic,
                        analysis.get('intent', ''),
                        check_result['problematic'],
                    )
                    revision_result = providers.generate_text(revision_prompt)
                    if not revision_result['success']:
                        update_research_status(
                            research_id,
                            status='failed',
                            stage='fact_checking',
                            error='Revision generation failed',
                        )
                        store_answer(research_id, answer_text, 'revision_failed')
                        send_progress('failed')
                        return
                    answer_text = writer.clean_answer(revision_result['text'])
                    store_answer(research_id, answer_text, 'revised')
                    logger.info(f"Revision {attempt+1} produced a new answer")
                else:
                    logger.warning(f"Fact check still failing after {max_revisions} revisions")
                    final_verification_status = 'fact_check_failed'

            if final_verification_status == 'verified':
                update_research_status(research_id, status='completed', stage='completed')
                store_answer(research_id, answer_text, 'verified')
                send_progress('completed')
                logger.info(f"Research {research_id} completed successfully")
                return

            # Reached here: still failing after revisions
            update_research_status(
                research_id,
                status='failed',
                stage='fact_checking',
                error='Fact check failed after max revisions',
            )
            store_answer(research_id, answer_text, 'fact_check_failed')
            send_progress('failed')
            return

        except Exception as e:
            logger.exception(f"Research {research_id} failed with exception")
            update_research_status(research_id, status='failed', stage='unknown', error=str(e))
            if progress_callback:
                progress_callback(research_id, 'failed')

def start_research(research_id, progress_callback=None, profile=None):
    """Start research in a separate thread, passing the callback and profile."""
    thread = threading.Thread(
        target=run_research,
        args=(research_id, progress_callback, profile),
        daemon=True,
    )
    thread.start()
    return thread