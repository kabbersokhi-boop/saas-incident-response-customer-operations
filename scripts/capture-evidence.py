#!/usr/bin/env python3
"""Capture public UI only using an existing private browser profile.

Requires Playwright and a local Chromium executable. Does not sign in, export
cookies, execute workflows, edit GHL, or capture credential panels.
"""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',required=True)
    parser.add_argument('--chromium',required=True)
    args=parser.parse_args()
    with sync_playwright() as p:
        context=p.chromium.launch_persistent_context(args.profile,headless=True,
            executable_path=args.chromium,args=['--no-sandbox'],
            viewport={'width':2000,'height':750},device_scale_factor=1.5)
        page=context.new_page()
        for wid,name in [('lhpMBpbBH3j4BDjm','customer-impact'),
                         ('tjUprwydaLuekcMg','customer-feedback'),
                         ('hRUiukB454KlQ2N6','approval-remediation')]:
            page.goto('http://localhost:5678/workflow/'+wid)
            page.locator('[data-test-id="zoom-to-fit"]').wait_for(timeout=30000)
            page.locator('[data-test-id="zoom-to-fit"]').click()
            page.wait_for_timeout(1000)
            assert '/signin' not in page.url
            page.screenshot(path=str(ROOT/'docs/evidence'/f'phase4-n8n-{name}.png'))
        page.set_viewport_size({'width':1600,'height':1100})
        page.goto('http://127.0.0.1:8001')
        page.wait_for_timeout(2000)
        assert 'RECOVERED' in page.locator('body').inner_text()
        page.screenshot(path=str(ROOT/'docs/evidence/phase4-control-center.png'))
        technical=page.locator('#live-incident-panel').bounding_box()
        customer=page.locator('#customer-recovery-panel').bounding_box()
        page.screenshot(path=str(ROOT/'docs/evidence/phase4-customer-recovery.png'),full_page=True,clip={
            'x':technical['x'],'y':technical['y'],'width':technical['width'],
            'height':customer['y']+customer['height']-technical['y']})
        context.close()
    print('Captured three real n8n editors and current RelayCart dashboard; review before publishing')

if __name__=='__main__':main()
