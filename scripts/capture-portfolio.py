#!/usr/bin/env python3
"""Capture real RelayCart/n8n views without executing or editing workflows.

Use an existing authenticated private Chromium profile. Review every output
before publication. HighLevel historical assets are curated separately.
"""
import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/evidence/portfolio'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--chromium', required=True)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            args.profile, executable_path=args.chromium, headless=True,
            args=['--no-sandbox'], viewport={'width':2000, 'height':1000},
            device_scale_factor=1.5)
        page = context.new_page()
        workflows = [
            ('OvrKKVaPxERgQNnr', 'IR 02', 'n8n-technical-response.png'),
            ('lhpMBpbBH3j4BDjm', 'GHL 01', 'n8n-ghl-impact-sync.png'),
            ('tjUprwydaLuekcMg', 'GHL 02', 'n8n-ghl-feedback.png'),
        ]
        for workflow_id, label, filename in workflows:
            # Long customer graphs need a wide canvas. Keep empty vertical space
            # small; full-resolution assets remain readable when opened directly.
            page.set_viewport_size({'width':1800 if label == 'IR 02' else 3200,
                                    'height':700})
            page.goto('http://localhost:5678/workflow/' + workflow_id)
            fit = page.locator('[data-test-id="zoom-to-fit"]')
            fit.wait_for(timeout=30000)
            assert label in page.locator('body').inner_text()
            fit.click()
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / filename))
        page.set_viewport_size({'width':1280, 'height':1100})
        page.goto('http://127.0.0.1:8001')
        page.locator('#customer-recovery-panel').wait_for()
        page.wait_for_function("document.querySelector('#customer-recovery-panel').innerText.includes('CONFIRMED_RESOLVED')")
        text = page.locator('body').inner_text()
        assert all(value in text for value in (
            'RECOVERED', 'Acme Bikes', 'Ocean Apparel', 'Green Dental',
            'CONFIRMED_RESOLVED', 'NEEDS_FOLLOW_UP', 'NOT AFFECTED'))
        technical = page.locator('#live-incident-panel').bounding_box()
        customer = page.locator('#customer-recovery-panel').bounding_box()
        page.screenshot(path=str(OUT / 'relaycart-final-recovery.png'),
                        full_page=True, clip={
                            'x':technical['x'], 'y':technical['y'],
                            'width':technical['width'],
                            'height':customer['y'] + customer['height'] - technical['y']})
        context.close()
    print('Captured four real application/editor views; visual privacy review required.')


if __name__ == '__main__':
    main()
