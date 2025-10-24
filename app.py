"""
Main Application Entry Point
Employee Check-in/Checkout System

This is the main Streamlit application that serves as the entry point
for the entire system. It handles:
- User authentication
- Session management
- Page routing
- Navigation

Usage:
    streamlit run app.py
"""

import streamlit as st
from datetime import datetime, timedelta

# Import services
from services.auth_service import AuthService
from database.db_manager import db_manager

# Import pages
from pages.employee_dashboard import render_employee_dashboard
from pages.admin_dashboard import render_admin_dashboard
from pages.reports import render_reports_page

# Import utilities
from utils.constants import SessionKeys, UserRole, UIConstants
from utils.logger import  get_logger, AppLogger
from config.config import Config

# Configure logger (optional - already configured via environment variables)
if hasattr(Config, 'LOG_LEVEL'):
    AppLogger.set_level(Config.LOG_LEVEL)

# Initialize logger
logger = get_logger(__name__)

# Initialize logger
logger = get_logger(__name__)

# ===== DATABASE INITIALIZATION ON STARTUP =====
# Ensure database exists before app runs
# This is critical for cloud deployments
from init_on_startup import ensure_database_exists
ensure_database_exists()


# ==================== Page Configuration ====================

def configure_page():
    """
    Configure Streamlit page settings.
    
    Sets page title, icon, layout, and initial sidebar state.
    """
    st.set_page_config(
        page_title=UIConstants.PAGE_TITLE,
        page_icon=UIConstants.PAGE_ICON,
        layout=UIConstants.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    logger.debug("Page configured")


# ==================== Session Management ====================

def init_session_state():
    """
    Initialize session state variables.
    
    Sets up all required session variables if they don't exist.
    """
    # Authentication state
    if SessionKeys.AUTHENTICATED.value not in st.session_state:
        st.session_state[SessionKeys.AUTHENTICATED.value] = False
        logger.debug("Session state initialized")
    
    # User information
    if SessionKeys.USER_ID.value not in st.session_state:
        st.session_state[SessionKeys.USER_ID.value] = None
    
    if SessionKeys.USERNAME.value not in st.session_state:
        st.session_state[SessionKeys.USERNAME.value] = None
    
    if SessionKeys.FULL_NAME.value not in st.session_state:
        st.session_state[SessionKeys.FULL_NAME.value] = None
    
    if SessionKeys.ROLE.value not in st.session_state:
        st.session_state[SessionKeys.ROLE.value] = None
    
    if SessionKeys.LOGIN_TIME.value not in st.session_state:
        st.session_state[SessionKeys.LOGIN_TIME.value] = None


def is_session_valid():
    """
    Check if current session is valid and not expired.
    
    Sessions expire after SESSION_TIMEOUT_HOURS from login time.
    
    Returns:
        bool: True if session is valid, False otherwise
    """
    if not st.session_state.get(SessionKeys.AUTHENTICATED.value):
        return False
    
    login_time = st.session_state.get(SessionKeys.LOGIN_TIME.value)
    if not login_time:
        return False
    
    # Check if session has expired
    elapsed_time = datetime.now() - login_time
    timeout = timedelta(hours=Config.SESSION_TIMEOUT_HOURS)
    
    if elapsed_time > timeout:
        logger.warning("Session expired")
        return False
    
    return True


def clear_session():
    """
    Clear all session state variables.
    
    Called during logout or session expiration.
    """
    logger.info("Clearing session")
    
    for key in [SessionKeys.AUTHENTICATED.value, SessionKeys.USER_ID.value,
                SessionKeys.USERNAME.value, SessionKeys.FULL_NAME.value,
                SessionKeys.ROLE.value, SessionKeys.LOGIN_TIME.value]:
        if key in st.session_state:
            del st.session_state[key]


# ==================== Authentication ====================

def render_login_page():
    """
    Render the login page.
    
    Displays login form and handles authentication.
    """
    logger.debug("Rendering login page")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🔐 Employee Check-in System")
        st.markdown("### Login to Continue")
        st.markdown("---")
        
        # Login form
        with st.form("login_form"):
            #bugfix: ensure that username is handled in "lowercase" only
            username = st.text_input("Username", placeholder="Enter your username", help="Username is case-insensitive")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submit = st.form_submit_button("🔑 Login", type="primary", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return
                
                # Authenticate user
                auth_service = AuthService()
                success, user, message = auth_service.authenticate(username, password)
                
                if success:
                    # Set session state
                    st.session_state[SessionKeys.AUTHENTICATED.value] = True
                    st.session_state[SessionKeys.USER_ID.value] = user.user_id
                    st.session_state[SessionKeys.USERNAME.value] = user.username
                    st.session_state[SessionKeys.FULL_NAME.value] = user.full_name
                    st.session_state[SessionKeys.ROLE.value] = user.role
                    st.session_state[SessionKeys.LOGIN_TIME.value] = datetime.now()
                    
                    logger.info(f"User logged in: {username} (Role: {user.role})")
                    
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error(message)
                    logger.warning(f"Failed login attempt for username: {username}")
        
        # Information section
        st.markdown("---")
        st.info("**Default Admin Credentials:**\n\nUsername: `admin`\nPassword: `admin123`\n\n"
                "⚠️ Please change the default password after first login!")


def render_sidebar():
    """
    Render the sidebar with navigation and user info.
    
    Displays user information, navigation menu, and logout button.
    """
    with st.sidebar:
        # User info
        st.markdown("### 👤 User Information")
        st.write(f"**Name:** {st.session_state.get(SessionKeys.FULL_NAME.value)}")
        st.write(f"**Username:** {st.session_state.get(SessionKeys.USERNAME.value)}")
        st.write(f"**Role:** {st.session_state.get(SessionKeys.ROLE.value).upper()}")
        
        st.markdown("---")
        
        # Navigation
        st.markdown("### 🧭 Navigation")
        
        user_role = st.session_state.get(SessionKeys.ROLE.value)
        
        if user_role == UserRole.ADMIN.value:
            page = st.radio(
                "Go to",
                ["Admin Dashboard", "Reports", "System Info"],
                label_visibility="collapsed"
            )
        else:
            page = st.radio(
                "Go to",
                ["Employee Dashboard", "Reports"],
                label_visibility="collapsed"
            )
        
        st.markdown("---")
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            username = st.session_state.get(SessionKeys.USERNAME.value)
            logger.info(f"User logged out: {username}")
            clear_session()
            st.rerun()
        
        # Session info
        st.markdown("---")
        st.caption(f"Session timeout: {Config.SESSION_TIMEOUT_HOURS} hours")
        login_time = st.session_state.get(SessionKeys.LOGIN_TIME.value)
        if login_time:
            st.caption(f"Logged in: {login_time.strftime('%Y-%m-%d %H:%M')}")
        
        return page


def render_system_info():
    """
    Render system information page (admin only).
    
    Displays application configuration and status.
    """
    st.title("ℹ️ System Information")
    st.markdown("---")
    
    # Application info
    st.subheader("📱 Application")
    st.write(f"**Name:** {Config.APP_NAME}")
    st.write(f"**Version:** {Config.APP_VERSION}")
    st.write(f"**Environment:** {'Development' if Config.DEVELOPMENT else 'Production'}")
    
    # Database info
    st.subheader("🗄️ Database")
    db_info = db_manager.get_engine_info()
    st.write(f"**Type:** {db_info['dialect'].upper()}")
    st.write(f"**Driver:** {db_info['driver']}")
    
    # Test connection
    if st.button("🔌 Test Database Connection"):
        with st.spinner("Testing connection..."):
            if db_manager.test_connection():
                st.success("✅ Database connection successful")
            else:
                st.error("❌ Database connection failed")
    
    # Configuration
    st.subheader("⚙️ Configuration")
    config_summary = Config.get_config_summary()
    for key, value in config_summary.items():
        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    
    # Logging
    st.subheader("📝 Logging")
    st.write(f"**Enabled:** {Config.LOGGING_ENABLED}")
    st.write(f"**Level:** {Config.LOG_LEVEL}")
    st.write(f"**Log Directory:** {Config.LOGS_DIR}")
    
    # Toggle logging
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🟢 Enable Logging"):
            LoggerConfig.enable_logging(True)
            st.success("Logging enabled")
    
    with col2:
        if st.button("🔴 Disable Logging"):
            LoggerConfig.enable_logging(False)
            st.warning("Logging disabled")


# ==================== Main Application ====================

def main():
    """
    Main application entry point.
    
    Handles routing and page rendering based on authentication
    and user role.
    """
    # Configure page
    configure_page()
    
    # Initialize session
    init_session_state()
    
    # Check authentication
    if not is_session_valid():
        render_login_page()
        return
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Route to appropriate page
    user_role = st.session_state.get(SessionKeys.ROLE.value)
    
    try:
        if user_role == UserRole.ADMIN.value:
            # Admin pages
            if selected_page == "Admin Dashboard":
                render_admin_dashboard()
            elif selected_page == "Reports":
                render_reports_page()
            elif selected_page == "System Info":
                render_system_info()
        else:
            # Employee pages
            if selected_page == "Employee Dashboard":
                render_employee_dashboard()
            elif selected_page == "Reports":
                render_reports_page()
    
    except Exception as e:
        logger.error(f"Error rendering page: {e}")
        st.error(f"An error occurred: {str(e)}")
        st.error("Please contact the administrator if this persists.")


# ==================== Application Entry Point ====================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Employee Check-in System")
    logger.info(f"Version: {Config.APP_VERSION}")
    logger.info(f"Environment: {'Development' if Config.DEVELOPMENT else 'Production'}")
    logger.info("=" * 60)
    
    try:
        main()
    except Exception as e:
        logger.critical(f"Critical error in main application: {e}")
        st.error("A critical error occurred. Please check the logs.")