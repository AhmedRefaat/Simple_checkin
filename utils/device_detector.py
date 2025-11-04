"""
Device Detection Utility
Detects mobile/tablet devices to restrict app access to desktop only.
"""

import re
import streamlit as st
from typing import Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


class DeviceDetector:
    """
    Utility class for detecting device types (mobile, tablet, desktop).
    """
    
    # Mobile device patterns
    MOBILE_PATTERNS = [
        r'Android.*Mobile',  # Android phones
        r'iPhone',           # iPhone
        r'iPod',             # iPod Touch
        r'Windows Phone',    # Windows Phone
        r'BlackBerry',       # BlackBerry
        r'webOS',            # Palm webOS
        r'Opera Mini',       # Opera Mini
        r'Opera Mobi',       # Opera Mobile
        r'IEMobile',         # IE Mobile
        r'Mobile.*Firefox',  # Firefox Mobile
    ]
    
    # Tablet patterns
    TABLET_PATTERNS = [
        r'iPad',                    # iPad
        r'Android(?!.*Mobile)',     # Android tablets
        r'Kindle',                  # Kindle
        r'Silk',                    # Amazon Silk
        r'PlayBook',                # BlackBerry PlayBook
        r'Tablet',                  # Generic tablet
    ]
    
    @staticmethod
    def get_user_agent() -> str:
        """
        Get User-Agent string from Streamlit request headers.
        
        Returns:
            str: User-Agent string or empty string if not available
        """
        try:
            # Try to get User-Agent from Streamlit context
            from streamlit.web.server.websocket_headers import _get_websocket_headers
            headers = _get_websocket_headers()
            
            if headers and 'User-Agent' in headers:
                return headers['User-Agent']
        except Exception as e:
            logger.debug(f"Could not get User-Agent from headers: {e}")
        
        # Fallback: Try session state (if set by JavaScript)
        if 'user_agent' in st.session_state:
            return st.session_state.user_agent
        
        return ""
    
    @staticmethod
    def is_mobile(user_agent: str = None) -> bool:
        """
        Check if device is a mobile phone.
        
        Args:
            user_agent: User-Agent string (auto-detected if None)
        
        Returns:
            bool: True if mobile device detected
        """
        if user_agent is None:
            user_agent = DeviceDetector.get_user_agent()
        
        if not user_agent:
            logger.warning("User-Agent not available, assuming desktop")
            return False
        
        # Check mobile patterns
        for pattern in DeviceDetector.MOBILE_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                logger.info(f"Mobile device detected: {user_agent}")
                return True
        
        return False
    
    @staticmethod
    def is_tablet(user_agent: str = None) -> bool:
        """
        Check if device is a tablet.
        
        Args:
            user_agent: User-Agent string (auto-detected if None)
        
        Returns:
            bool: True if tablet device detected
        """
        if user_agent is None:
            user_agent = DeviceDetector.get_user_agent()
        
        if not user_agent:
            return False
        
        # Check tablet patterns
        for pattern in DeviceDetector.TABLET_PATTERNS:
            if re.search(pattern, user_agent, re.IGNORECASE):
                logger.info(f"Tablet device detected: {user_agent}")
                return True
        
        return False
    
    @staticmethod
    def is_desktop(user_agent: str = None) -> bool:
        """
        Check if device is a desktop/PC.
        
        Args:
            user_agent: User-Agent string (auto-detected if None)
        
        Returns:
            bool: True if desktop device (not mobile or tablet)
        """
        return not (DeviceDetector.is_mobile(user_agent) or DeviceDetector.is_tablet(user_agent))
    
    @staticmethod
    def get_device_type(user_agent: str = None) -> str:
        """
        Get device type as string.
        
        Args:
            user_agent: User-Agent string (auto-detected if None)
        
        Returns:
            str: 'mobile', 'tablet', or 'desktop'
        """
        if DeviceDetector.is_mobile(user_agent):
            return 'mobile'
        elif DeviceDetector.is_tablet(user_agent):
            return 'tablet'
        else:
            return 'desktop'
    
    @staticmethod
    def inject_device_detector_js() -> None:
        """
        Inject JavaScript to detect device type and screen size.
        Stores results in Streamlit session state.
        """
        import streamlit.components.v1 as components
        
        js_code = """
        <script>
        // Get User-Agent
        const userAgent = navigator.userAgent;
        
        // Get screen dimensions
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        
        // Get viewport dimensions
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Check if touch device
        const isTouchDevice = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
        
        // Simple mobile detection
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        
        // Check screen width (mobile typically < 768px, tablet < 1024px)
        const isMobileScreen = screenWidth < 768;
        const isTabletScreen = screenWidth >= 768 && screenWidth < 1024;
        
        // Log detection results
        console.log('Device Detection:', {
            userAgent: userAgent,
            screenWidth: screenWidth,
            isMobile: isMobile || isMobileScreen,
            isTablet: isTabletScreen,
            isTouchDevice: isTouchDevice
        });
        
        // Send to Streamlit (if needed, can use st.experimental_set_query_params)
        // Note: This is for logging/debugging only
        // Streamlit backend detection is primary method
        </script>
        """
        
        components.html(js_code, height=0)


def render_desktop_only_blocker(allow_tablet: bool = False) -> bool:
    """
    Check if device is desktop and block if mobile/tablet.
    
    Args:
        allow_tablet: If True, allow tablet access (only block phones)
    
    Returns:
        bool: True if device is allowed, False if blocked
    """
    detector = DeviceDetector()
    device_type = detector.get_device_type()
    
    # Inject JavaScript for enhanced detection (optional)
    detector.inject_device_detector_js()
    
    # Check if device is allowed
    if device_type == 'mobile':
        st.error("📱 **Mobile Access Not Allowed**")
        st.warning("""
        ### 🖥️ Desktop Browser Required
        
        This application is optimized for desktop/PC browsers only.
        
        **Why?**
        - Complex forms and data entry
        - Large tables and reports
        - Better keyboard input accuracy
        - Optimized for larger screens
        
        **How to access:**
        1. Open this link on your desktop/laptop computer
        2. Use Chrome, Firefox, Edge, or Safari
        3. Bookmark the URL for easy access
        
        ---
        **App URL:** `https://ra-arch-checkin.streamlit.app/`
        """)
        
        # Optional: Show QR code for easy URL transfer
        st.info("💡 **Tip:** Email this URL to yourself or use a QR code scanner to transfer to desktop")
        
        st.stop()  # Stop execution
        return False
    
    elif device_type == 'tablet' and not allow_tablet:
        st.warning("📱 **Tablet Access Limited**")
        st.info("""
        ### 🖥️ Desktop Browser Recommended
        
        While tablets are supported, this app works best on desktop/laptop computers.
        
        You can continue, but some features may not display optimally.
        """)
        
        # Allow tablet access but show warning
        if st.button("✅ Continue on Tablet (Not Recommended)"):
            st.session_state['tablet_override'] = True
            st.rerun()
        
        if not st.session_state.get('tablet_override', False):
            st.stop()
            return False
    
    # Desktop or allowed device
    logger.info(f"Device allowed: {device_type}")
    return True