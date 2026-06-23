"""
Automation Bot for Threads (Meta) and Shopee Affiliate

Session-First Architecture:
- NO automatic login retries
- Uses pre-authenticated session cookies
- Validates session before use
- Stops if session is expired (no retry)

This eliminates the login loop problem caused by trust-layer rejection.
"""

import logging
import os
import sys

from dotenv import load_dotenv

from services.session_manager import SessionManager, ThreadsAuth, SessionStatus
from services.feed_explorer import FeedExplorer
from services.network_discovery import NetworkDiscovery

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║         Threads & Shopee Affiliate Automation Bot           ║
║                                                              ║
║  Session-First Architecture (no auto login)                ║
╚══════════════════════════════════════════════════════════════╝
"""


def initialize_session() -> tuple[bool, SessionManager | None]:
    """
    Initialize session using SessionManager.
    
    Flow:
    1. Load session from env/file
    2. Validate session
    3. If valid → return session manager
    4. If expired → STOP
    5. If rate_limited/unknown → preserve session, continue with warning
    
    Returns:
        (success, session_manager)
    """
    logger.info("=" * 60)
    logger.info("INITIALIZING SESSION")
    logger.info("=" * 60)
    
    # Create session manager
    session_manager = SessionManager()
    
    # Step 1: Load session
    logger.info("\n[Step 1] Loading session from env/file...")
    if not session_manager.load_session():
        return False, None
    
    # Step 2: Validate session
    logger.info("\n[Step 2] Validating session...")
    result = session_manager.validate_session()
    
    if result.status == SessionStatus.VALID:
        logger.info(f"[SESSION] VALID")
        logger.info(f"  Status: {result.status.value}")
        logger.info(f"  User ID: {result.user_id or 'N/A'}")
        return True, session_manager
    
    elif result.status == SessionStatus.EXPIRED:
        # Session explicitly expired - STOP
        logger.error(f"[SESSION] EXPIRED: {result.reason}")
        return False, None
    
    elif result.status == SessionStatus.RATE_LIMITED:
        # Rate limited - DO NOT STOP, preserve session
        logger.warning(f"[SESSION] RATE LIMITED: {result.reason}")
        logger.warning("[SESSION] Session preserved - will retry later")
        if result.retry_after:
            logger.warning(f"[SESSION] Retry-After: {result.retry_after}s")
        # Continue with session (may work for non-validation requests)
        return True, session_manager
    
    elif result.status == SessionStatus.UNKNOWN:
        # Unknown state - preserve session
        logger.warning(f"[SESSION] UNKNOWN: {result.reason}")
        logger.warning("[SESSION] Session preserved - proceeding with caution")
        return True, session_manager
    
    else:
        # Other invalid states
        logger.error(f"[SESSION] {result.status.value}: {result.reason}")
        return False, None


def run_automation(session_manager: SessionManager):
    """
    Run automation tasks with valid session.
    
    Uses Playwright to capture browser network traffic for endpoint discovery.
    
    Args:
        session_manager: Validated SessionManager instance
    """
    logger.info("\n" + "=" * 60)
    logger.info("RUNNING AUTOMATION")
    logger.info("=" * 60)
    
    # Get authenticated session cookies
    cookies = session_manager.get_cookies()
    
    if not cookies:
        logger.error("Failed to get session cookies")
        return False
    
    logger.info(f"[✓] Authenticated session ready with {len(cookies)} cookies")
    
    # Run Network Discovery with Playwright
    logger.info("\n[*] Running Playwright Network Discovery...")
    logger.info("[*] This captures ALL browser network traffic (30s capture)")
    
    try:
        discovery = NetworkDiscovery(cookies)
        discovery.capture(duration_seconds=30)
        
        # Save results
        logger.info("\n[*] Saving discovery results...")
        discovery.save_results(
            network_file="network_capture.json",
            feed_file="feed_candidates.json",
            graphql_file="graphql_candidates.json"
        )
        
        # Generate report
        logger.info("\n[*] Generating discovery report...")
        report = discovery.generate_report("NETWORK_DISCOVERY_REPORT.md")
        
        # Print summary
        discovery.print_summary(report)
        
        logger.info("\n[✓] Network discovery complete!")
        logger.info("[*] Files generated:")
        logger.info("    - network_capture.json")
        logger.info("    - feed_candidates.json")
        logger.info("    - graphql_candidates.json")
        logger.info("    - NETWORK_DISCOVERY_REPORT.md")
        
    except Exception as e:
        logger.error(f"[!] Network discovery failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True



def main():
    """Main entry point for the automation bot."""
    print(BANNER)

    try:
        # Initialize session (NO AUTO LOGIN)
        success, session_manager = initialize_session()
        
        if not success:
            # Session invalid - show manual refresh instructions
            print("\n" + "=" * 60)
            print("🚫 SESSION EXPIRED")
            print("=" * 60)
            print("\nTo refresh your session:")
            print("   1. Open browser to https://www.instagram.com")
            print("   2. Login and complete any verification (2FA, email)")
            print("   3. Press F12 → Application → Cookies → instagram.com")
            print("   4. Copy these cookies to .env:")
            print("      - sessionid")
            print("      - csrftoken")
            print("      - ds_user_id")
            print("      - mid")
            print("      - ig_did")
            print("   5. Run this script again")
            print("=" * 60 + "\n")
            return 1
        
        # Session valid - run automation
        threads_success = run_automation(session_manager)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Threads Session:       {'✓ PASS' if threads_success else '✗ FAIL'}")
        logger.info("=" * 60)

        if threads_success:
            logger.info("All tests passed!")
            return 0
        else:
            logger.warning("Some tests failed. Check logs for details.")
            return 1

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
