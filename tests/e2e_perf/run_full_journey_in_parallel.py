"""Load test: 10 parallel users running the full model building workflow.

Usage:
    # Start Django server first:
    poetry run python manage.py runserver

    # Run load test (default: localhost:8000):
    poetry run python tests/e2e_perf/load_test_full_journey.py

    # Run against different host:
    poetry run python tests/e2e_perf/run_full_journey_in_parallel.py --base-url https://dev.e-footprint.boavizta.org
"""
import argparse
import asyncio
import random
import time
from dataclasses import dataclass, field

from playwright.async_api import async_playwright, Page, expect

DEFAULT_BASE_URL = "http://localhost:8000"
NUM_USERS = 10
RUNS_PER_USER = 5
MIN_WAIT_SECONDS = 1
MAX_WAIT_SECONDS = 10
DEFAULT_TIMEOUT_MS = 5000


@dataclass
class UserStats:
    user_id: int
    successful_runs: int = 0
    failed_runs: int = 0
    run_times: list = field(default_factory=list)
    errors: list = field(default_factory=list)


async def click_and_wait_for_htmx(page: Page, locator):
    """Click an HTMX element and wait for its request to complete."""
    await asyncio.sleep(0.02)
    hx_url = await locator.get_attribute("hx-get") or await locator.get_attribute("hx-post")
    if hx_url:
        async with page.expect_response(lambda r: hx_url in r.url):
            await locator.click()
    else:
        await locator.click()


async def run_full_journey(page: Page, run_number: int, user_id: int) -> None:
    """Execute the complete model building workflow (async version).

    This replicates test_complete_model_building_workflow from test_full_journey.py.
    """
    # Object names - unique per user/run to avoid conflicts
    suffix = f"U{user_id}R{run_number}"
    uj_name_one = f"Test E2E UJ 1 {suffix}"
    uj_name_two = f"Test E2E UJ 2 {suffix}"
    step_one = f"Test E2E Step 1 {suffix}"
    step_two = f"Test E2E Step 2 {suffix}"
    server_name = f"Test E2E Server {suffix}"
    service_name = f"Test E2E Service {suffix}"
    job_one = f"Test E2E Job 1 {suffix}"
    job_two = f"Test E2E Job 2 {suffix}"
    up_name = f"Test E2E Usage Pattern {suffix}"

    # Helper locators
    side_panel = page.locator("#sidePanel")
    side_panel_form = page.locator("#sidePanelForm")
    submit_button = page.locator("#btn-submit-form")

    async def fill_field(field_id: str, value: str, clear_first: bool = True):
        field = page.locator(f"#{field_id}")
        if clear_first:
            await field.clear()
        await field.fill(value)

    async def select_option(field_id: str, value: str):
        await page.locator(f"#{field_id}").select_option(value)

    async def submit_and_wait_for_close():
        await submit_button.click()
        await side_panel_form.wait_for(state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    async def get_object_card(object_type: str, name: str):
        return page.locator(f"div[id^='{object_type}-']").filter(has_text=name)

    async def click_delete_in_panel():
        await click_and_wait_for_htmx(page, side_panel.locator("button[hx-get*='ask-delete-object']"))

    async def confirm_delete():
        await click_and_wait_for_htmx(page, page.get_by_role("button", name="Yes, delete"))
        await page.locator("#model-builder-modal").wait_for(state="hidden", timeout=DEFAULT_TIMEOUT_MS)

    # --- Navigate to model builder with fresh session ---
    await page.goto("/")
    await page.locator("#btn-start-modeling-my-service").click()
    await page.locator("#btn-reboot-modeling").click()
    await page.locator("#model-canva").wait_for(state="visible")

    # --- Create two usage journeys ---
    await click_and_wait_for_htmx(page, page.locator("#btn-add-usage-journey"))
    await fill_field("UsageJourney_name", uj_name_one)
    await submit_and_wait_for_close()

    await click_and_wait_for_htmx(page, page.locator("#btn-add-usage-journey"))
    await fill_field("UsageJourney_name", uj_name_two)
    await submit_and_wait_for_close()

    # --- Add two steps to UJ 1 ---
    uj_card = await get_object_card("UsageJourney", uj_name_one)
    await click_and_wait_for_htmx(page, uj_card.locator("div[id^='add-step-to']"))
    await expect(side_panel).to_contain_text("Add new usage journey step")
    await fill_field("UsageJourneyStep_name", step_one)
    await fill_field("UsageJourneyStep_user_time_spent", "10.1", clear_first=False)
    await submit_and_wait_for_close()

    await click_and_wait_for_htmx(page, uj_card.locator("div[id^='add-step-to']"))
    await fill_field("UsageJourneyStep_name", step_two)
    await fill_field("UsageJourneyStep_user_time_spent", "20.2", clear_first=False)
    await submit_and_wait_for_close()

    # --- Create server ---
    await click_and_wait_for_htmx(page, page.locator("#btn-add-server"))
    await expect(side_panel).to_contain_text("Add new server")
    await side_panel_form.locator("#type_object_available").first.select_option("BoaviztaCloudServer")
    await fill_field("BoaviztaCloudServer_name", server_name)
    await fill_field("BoaviztaCloudServer_instance_type", "ent1-l")
    await submit_and_wait_for_close()

    # --- Add service to server ---
    server_card = await get_object_card("BoaviztaCloudServer", server_name)
    await click_and_wait_for_htmx(page, server_card.locator("button[id^='add-service-to']"))
    await fill_field("WebApplication_name", service_name)
    await select_option("WebApplication_technology", "php-symfony")
    await submit_and_wait_for_close()

    # --- Add job to step 1 ---
    step_card_one = await get_object_card("UsageJourneyStep", step_one)
    await click_and_wait_for_htmx(page, step_card_one.locator("button[hx-get*='open-create-object-panel/JobBase']"))
    await page.locator("#service").wait_for(state="attached")
    await select_option("service", service_name)
    await fill_field("WebApplicationJob_name", job_one)
    await submit_and_wait_for_close()

    # --- Add job to step 2 (direct server call) ---
    step_card_two = await get_object_card("UsageJourneyStep", step_two)
    await click_and_wait_for_htmx(page, step_card_two.locator("button[hx-get*='open-create-object-panel/JobBase']"))
    await page.locator("#service").wait_for(state="attached")
    await select_option("service", "direct_server_call")
    await fill_field("Job_name", job_two)
    await submit_and_wait_for_close()

    # --- Create usage pattern with timeseries ---
    await click_and_wait_for_htmx(page, page.locator("#add_usage_pattern"))
    await fill_field("UsagePattern_name", up_name)
    await page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").fill("2")
    await page.locator("#UsagePattern_hourly_usage_journey_starts__modeling_duration_value").dispatch_event("change")
    await page.locator("#UsagePattern_hourly_usage_journey_starts__initial_volume").fill("1000")
    await page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").fill("25")
    await page.locator("#UsagePattern_hourly_usage_journey_starts__net_growth_rate_in_percentage").dispatch_event("change")
    await select_option("UsagePattern_hourly_usage_journey_starts__net_growth_rate_timespan", "year")
    await select_option("UsagePattern_usage_journey", uj_name_one)
    await submit_and_wait_for_close()

    # --- Delete unused UJ 2 ---
    uj_card_two = await get_object_card("UsageJourney", uj_name_two)
    await click_and_wait_for_htmx(page, uj_card_two.locator("button[id^='button-']").first)
    await click_delete_in_panel()
    await confirm_delete()

    # --- Delete default UJ ---
    default_uj = "My first usage journey"
    default_uj_card = await get_object_card("UsageJourney", default_uj)
    await click_and_wait_for_htmx(page, default_uj_card.locator("button[id^='button-']").first)
    await click_delete_in_panel()
    await confirm_delete()

    # --- Open and close results panel ---
    await click_and_wait_for_htmx(page, page.locator("#btn-open-panel-result"))
    await page.locator("#lineChart").wait_for(state="visible")
    await page.wait_for_timeout(100)
    await expect(page.locator("#graph-block")).to_be_visible()
    await expect(page.locator("#result-block")).to_be_visible()

    await page.locator("#result-block div[onclick='hidePanelResult()']").click()
    await expect(page.locator("#lineChart")).not_to_be_visible()

    # --- Delete usage pattern ---
    up_card = await get_object_card("UsagePattern", up_name)
    await click_and_wait_for_htmx(page, up_card.locator("button[id^='button-']").first)
    await click_delete_in_panel()
    await confirm_delete()


async def simulate_user(user_id: int, base_url: str) -> UserStats:
    """Simulate a single user running the workflow multiple times."""
    stats = UserStats(user_id=user_id)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for run in range(RUNS_PER_USER):
            # Fresh browser context (new session) for each run
            context = await browser.new_context(base_url=base_url)
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)

            start_time = time.time()
            try:
                print(f"[User {user_id}] Starting run {run + 1}/{RUNS_PER_USER}")
                await run_full_journey(page, run, user_id)
                elapsed = time.time() - start_time
                stats.successful_runs += 1
                stats.run_times.append(elapsed)
                print(f"[User {user_id}] Run {run + 1} completed in {elapsed:.2f}s")
            except Exception as e:
                elapsed = time.time() - start_time
                stats.failed_runs += 1
                stats.errors.append(f"Run {run + 1}: {type(e).__name__}: {e}")
                print(f"[User {user_id}] Run {run + 1} FAILED after {elapsed:.2f}s: {e}")
            finally:
                await context.close()

            # Random wait between runs (except after last run)
            if run < RUNS_PER_USER - 1:
                wait_time = random.uniform(MIN_WAIT_SECONDS, MAX_WAIT_SECONDS)
                print(f"[User {user_id}] Waiting {wait_time:.1f}s before next run")
                await asyncio.sleep(wait_time)

        await browser.close()

    return stats


async def main(base_url: str):
    """Run the load test with multiple parallel users."""
    print(f"\n{'='*60}")
    print(f"Load Test: {NUM_USERS} parallel users, {RUNS_PER_USER} runs each")
    print(f"Target: {base_url}")
    print(f"Wait between runs: {MIN_WAIT_SECONDS}-{MAX_WAIT_SECONDS}s (random)")
    print(f"{'='*60}\n")

    start_time = time.time()

    # Run all users in parallel
    tasks = [simulate_user(i, base_url) for i in range(NUM_USERS)]
    results = await asyncio.gather(*tasks)

    total_time = time.time() - start_time

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    total_successful = sum(r.successful_runs for r in results)
    total_failed = sum(r.failed_runs for r in results)
    all_times = [t for r in results for t in r.run_times]

    print(f"Total time: {total_time:.2f}s")
    print(f"Total runs: {total_successful + total_failed}")
    print(f"Successful: {total_successful}")
    print(f"Failed: {total_failed}")

    if all_times:
        print(f"\nRun time stats (successful runs):")
        print(f"  Min: {min(all_times):.2f}s")
        print(f"  Max: {max(all_times):.2f}s")
        print(f"  Avg: {sum(all_times) / len(all_times):.2f}s")

    # Print errors if any
    all_errors = [(r.user_id, err) for r in results for err in r.errors]
    if all_errors:
        print(f"\nErrors ({len(all_errors)} total):")
        for user_id, error in all_errors:
            print(f"  [User {user_id}] {error}")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test for e-footprint interface")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--users", type=int, default=NUM_USERS, help=f"Number of parallel users (default: {NUM_USERS})")
    parser.add_argument("--runs", type=int, default=RUNS_PER_USER, help=f"Runs per user (default: {RUNS_PER_USER})")
    args = parser.parse_args()

    # Allow overriding globals via CLI
    NUM_USERS = args.users
    RUNS_PER_USER = args.runs

    asyncio.run(main(args.base_url))
