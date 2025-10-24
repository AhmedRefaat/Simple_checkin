"""
Employee Dashboard Page
Provides employee interface for check-in/check-out and viewing attendance.

Features:
- Check-in/Check-out buttons
- Current day status
- Current month attendance view
- Last 5 working days from previous month (if before 8th)
- Add comments and extra expenses
- View monthly statistics

Usage:
    This module is imported and called by the main app.py
"""

import streamlit as st
from datetime import date, datetime
import pandas as pd

from services.checkin_service import CheckinService
from services.report_service import ReportService
from services.calculation_service import CalculationService
from services.auth_service import AuthService  # add this to auth-user using auth_service ➡️ part of feature/change_user_password
from utils.helpers import TimeHelper, CurrencyHelper
from utils.constants import SessionKeys, DayType
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class EmployeeDashboard:
    """
    Employee dashboard interface.
    
    Provides employees with:
    - Check-in/Check-out functionality
    - View attendance records
    - Add comments and expenses
    - View monthly statistics
    """
    
    def __init__(self):
        """Initialize employee dashboard with required services"""
        self.checkin_service = CheckinService()
        self.report_service = ReportService()
        self.calculator = CalculationService()
        self.auth_service = AuthService()  # add this to auth-user using auth_service ➡️ part of feature/change_user_password
        logger.debug("EmployeeDashboard initialized")
    
    def render(self):
        """
        Render the employee dashboard page.
        
        Main entry point for displaying employee interface.
        """
        logger.info(f"Rendering employee dashboard for user: {st.session_state.get(SessionKeys.USERNAME.value)}")
        
        # Page header
        st.title("👤 Employee Dashboard")
        st.markdown(f"**Welcome, {st.session_state.get(SessionKeys.FULL_NAME.value)}!**")
        st.markdown("---")
        
        # [bugfix] add sidebar selectbox for supported features for the employee dashboard
        # this is added as part of feature/change_user_password
        # Sidebar for navigation
        page = st.sidebar.selectbox(
            "📋 Select Function",
            [
                "Today's Status",
                "Monthly Report",
                "Full History",
                "Change Password"
            ]
        )
        
        # Render selected page
        if page == "Today's Status":
            self._render_today_status()
        elif page == "Monthly Report":
            self._render_monthly_report()
        elif page == "Full History":
            self._render_full_history()
        elif page == "Change Password":
            self._render_change_password()
    
    # ============================= feature: show today employee's today-status =============================
    # this is added as part of feature/change_user_password
    def _render_today_status(self):
        """
        Render today's status page with check-in/out and current info.
        
        This is the default view showing all current day functionality.
        """
        # Get user ID from session
        user_id = st.session_state.get(SessionKeys.USER_ID.value)
        
        if not user_id:
            st.error("Session expired. Please log in again.")
            logger.error("User ID not found in session")
            return
        
        # Layout: Two columns for main actions
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_check_in_section(user_id)
        
        with col2:
            self._render_current_status(user_id)
        
        st.markdown("---")
        
        # Attendance records section
        self._render_attendance_records(user_id)
        
        st.markdown("---")
        
        # Monthly statistics section
        self._render_monthly_statistics(user_id)

    # ============================= feature: show monthly employee's status =============================
    # this is added as part of feature/change_user_password

    def _render_monthly_report(self):
        """
        Render monthly report page with month/year selection.
        
        Allows employees to view any month's statistics and salary breakdown.
        """
        st.header("📊 Monthly Report")
        
        # Get user ID from session
        user_id = st.session_state.get(SessionKeys.USER_ID.value)
        
        if not user_id:
            st.error("Session expired. Please log in again.")
            return
        
        # Month selection
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Get report
        report = self.report_service.get_monthly_report(user_id, year, month)
        
        if not report:
            st.info("No data available for this month")
            return
        
        # Display report header
        st.subheader(f"📅 {report['month_name']} {report['year']}")
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Working Days", f"{report['actual_working_days']} / {report['expected_working_days']}")
        
        with col2:
            st.metric("Absence Days", report['absence_days'])
        
        with col3:
            st.metric("Total Time", f"{report['working_hours']}h {report['working_minutes']}m")
        
        with col4:
            ot_total = report['overtime_minutes']
            if ot_total != 0:
                ot_sign = "+" if ot_total > 0 else ""
                ot_h, ot_m = self.calculator.format_minutes_to_hours_minutes(abs(ot_total))
                st.metric("Total Overtime", f"{ot_sign}{ot_h}h {ot_m}m")
            else:
                st.metric("Total Overtime", "0h 0m")
        
        # Financial summary
        st.markdown("---")
        st.subheader("💰 Financial Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Expenses", CurrencyHelper.format_currency(report['extra_expenses']))
        
        with col2:
            st.metric("Bonus", CurrencyHelper.format_currency(report['bonus']))
            st.caption("Set by admin")
        
        with col3:
            st.metric("Total Salary", CurrencyHelper.format_currency(report['salary']))
        
        # Show calculation breakdown
        with st.expander("📊 Salary Calculation Breakdown"):
            st.write(f"**Total Working Minutes:** {report['total_working_minutes']} minutes")
            st.write(f"**Minute Cost:** {report['minute_cost']} EGP/minute")
            st.write(f"**Base Salary:** {report['total_working_minutes']} × {report['minute_cost']} = "
                    f"{report['total_working_minutes'] * report['minute_cost']:.2f} EGP")
            st.write(f"**Extra Expenses:** {report['extra_expenses']:.2f} EGP")
            st.write(f"**Bonus (admin-set):** {report['bonus']:.2f} EGP")
            st.write(f"**TOTAL:** {report['salary']:.2f} EGP")

    # ============================= feature: show full-history employee's status =============================
    # this is added as part of feature/change_user_password

    def _render_full_history(self):
        """
        Render full work history page.
        
        Shows career-wide statistics and monthly breakdown table.
        """
        st.header("📜 Full Work History")
        
        # Get user ID from session
        user_id = st.session_state.get(SessionKeys.USER_ID.value)
        
        if not user_id:
            st.error("Session expired. Please log in again.")
            return
        
        # Get full report
        report = self.report_service.get_full_report(user_id)
        
        if not report:
            st.info("No data available")
            return
        
        # Display employee info
        st.write(f"**Name:** {report['user_name']}")
        st.write(f"**Join Date:** {report['join_date']}")
        st.write(f"**Minute Cost:** {report['minute_cost']} EGP/min")
        
        # Display cumulative stats
        st.markdown("---")
        st.subheader("📈 Career Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Working Days", report['cumulative_stats']['total_working_days'])
        with col2:
            st.metric("Total Hours", report['cumulative_stats']['total_working_hours'])
        with col3:
            st.metric("Total Bonus", CurrencyHelper.format_currency(report['cumulative_stats']['total_bonus']))
        with col4:
            st.metric("Total Salary", CurrencyHelper.format_currency(report['cumulative_stats']['total_salary']))
        
        # Monthly breakdown table
        st.markdown("---")
        st.subheader("📅 Monthly Breakdown")
        
        if report['monthly_summaries']:
            data = []
            for summary in report['monthly_summaries']:
                data.append({
                    'Month': f"{summary['month_name']} {summary['year']}",
                    'Working Days': summary['working_days'],
                    'Absence Days': summary['absence_days'],
                    'Total Hours': summary['working_hours'],
                    'Bonus (EGP)': f"{summary['bonus']:.2f}",
                    'Salary (EGP)': f"{summary['salary']:.2f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No monthly data available")

    
    # ============================= feature: change the employee password =============================
    # this is added as part of feature/change_user_password

    def _render_change_password(self):
        """
        Render password change form for employee.
        
        Allows employees to change their own password with validation.
        """
        st.header("🔐 Change Password")
        
        # Get user ID from session state
        user_id = st.session_state.get(SessionKeys.USER_ID.value)
        
        if not user_id:
            st.error("Session expired. Please log in again.")
            return
        
        st.info("ℹ️ Password must be at least 6 characters long")
        
        with st.form("change_password_form"):
            current_password = st.text_input(
                "Current Password*",
                type="password",
                placeholder="Enter your current password"
            )
            
            new_password = st.text_input(
                "New Password*",
                type="password",
                placeholder="Enter new password (min 6 characters)"
            )
            
            confirm_password = st.text_input(
                "Confirm New Password*",
                type="password",
                placeholder="Re-enter new password"
            )
            
            submitted = st.form_submit_button("🔒 Change Password", type="primary")
            
            if submitted:
                # Validation
                if not current_password or not new_password or not confirm_password:
                    st.error("❌ All fields are required")
                elif new_password != confirm_password:
                    st.error("❌ New passwords do not match")
                elif len(new_password) < 6:
                    st.error("❌ New password must be at least 6 characters long")
                else:
                    # Call auth service to change password
                    success, message = self.auth_service.change_password(
                        user_id,
                        current_password,
                        new_password
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("🔄 Please log out and log in again with your new password")
                    else:
                        st.error(f"❌ {message}")
        
        # Security tips
        st.markdown("---")
        st.subheader("🛡️ Password Security Tips")
        st.markdown("""
        - Use a mix of uppercase, lowercase, numbers, and symbols
        - Avoid using personal information
        - Don't reuse passwords from other accounts
        - Change your password regularly
        - Never share your password with anyone
        """)

    
    def _render_check_in_section(self, user_id: int):
        """
        Render check-in/check-out action section.
        
        Displays buttons for check-in and check-out based on current status.
        
        Args:
            user_id: User ID
        """
        st.subheader("📍 Check-In / Check-Out")
        
        # Get current status
        status = self.checkin_service.get_current_status(user_id)
        
        # Check-in button
        if not status['checked_in']:
            if st.button("🟢 Check In Now", type="primary", use_container_width=True):
                success, attendance, message = self.checkin_service.check_in(user_id)
                
                if success:
                    st.success(message)
                    logger.info(f"User {user_id} checked in successfully")
                    st.rerun()
                else:
                    st.error(message)
                    logger.warning(f"Check-in failed for user {user_id}: {message}")
        else:
            st.success("✅ You are checked in!")
            
            # Check-out button
            if not status['checked_out']:
                if st.button("🔴 Check Out Now", type="secondary", use_container_width=True):
                    success, attendance, message = self.checkin_service.check_out(user_id)
                    
                    if success:
                        st.success(message)
                        logger.info(f"User {user_id} checked out successfully")
                        st.rerun()
                    else:
                        st.error(message)
                        logger.warning(f"Check-out failed for user {user_id}: {message}")
            else:
                st.info("✅ You have checked out for today")
    
    def _render_current_status(self, user_id: int):
        """
        Render current day status information.
        
        Shows today's check-in/out times and working hours.
        
        Args:
            user_id: User ID
        """
        st.subheader("📊 Today's Status")
        
        # Get current status
        status = self.checkin_service.get_current_status(user_id)
        
        if status['checked_in']:
            # Display check-in time
            check_in_str = status['check_in_time'].strftime('%H:%M') if status['check_in_time'] else "N/A"
            st.metric("Check-In Time", check_in_str)
            
            # Show late indicator
            if status['is_late']:
                st.warning("⚠️ Late arrival (after 9:30 AM)")
            
            # Display check-out time
            if status['checked_out']:
                check_out_str = status['check_out_time'].strftime('%H:%M') if status['check_out_time'] else "N/A"
                st.metric("Check-Out Time", check_out_str)
                
                # Display working hours
                st.metric("Working Time", f"{status['working_hours']}h {status['working_minutes']}m")
                
                # Display overtime (view only for employee)
                if status['overtime_minutes'] != 0:
                    overtime_sign = "+" if status['overtime_minutes'] > 0 else ""
                    ot_hours, ot_mins = self.calculator.format_minutes_to_hours_minutes(abs(status['overtime_minutes']))
                    st.metric("Overtime", f"{overtime_sign}{ot_hours}h {ot_mins}m")
                    st.caption("ℹ️ Overtime is adjusted by admin")
            else:
                # Show current working time (live)
                st.metric("Current Working Time", f"{status['working_hours']}h {status['working_minutes']}m")
                st.caption("⏱️ Timer running...")
        else:
            st.info("Not checked in yet today")
    
    def _render_attendance_records(self, user_id: int):
        """
        Render attendance records table.
        
        Shows current month and last 5 working days from previous month
        (if current date is <= 8th of the month).
        
        Args:
            user_id: User ID
        """
        st.subheader("📅 Attendance Records")
        
        # Get attendance records
        records = self.report_service.get_current_month_with_last_days(user_id)
        
        if not records:
            st.info("No attendance records found")
            return
        
        # Prepare data for display
        data = []
        for record in records:
            # Format times
            check_in = record.check_in_time.strftime('%H:%M') if record.check_in_time else "-"
            check_out = record.check_out_time.strftime('%H:%M') if record.check_out_time else "-"
            
            # Format working time
            hours, mins = self.calculator.format_minutes_to_hours_minutes(record.total_working_minutes)
            working_time = f"{hours}h {mins}m" if record.total_working_minutes > 0 else "-"
            
            # Format overtime (view only)
            if record.overtime_minutes != 0:
                ot_sign = "+" if record.overtime_minutes > 0 else ""
                ot_hours, ot_mins = self.calculator.format_minutes_to_hours_minutes(abs(record.overtime_minutes))
                overtime_str = f"{ot_sign}{ot_hours}h {ot_mins}m"
            else:
                overtime_str = "-"
            
            # Format expenses
            expenses = CurrencyHelper.format_currency(record.extra_expenses) if record.extra_expenses > 0 else "-"
            
            # Day type badge
            day_type_display = record.day_type.replace('_', ' ').title()
            
            # Late indicator
            late_indicator = "🔴" if record.is_late else ""
            
            data.append({
                'Date': record.attendance_date.strftime('%Y-%m-%d'),
                'Day': record.attendance_date.strftime('%A'),
                'Check-In': f"{late_indicator} {check_in}" if late_indicator else check_in,
                'Check-Out': check_out,
                'Working Time': working_time,
                'Overtime': overtime_str,
                'Expenses': expenses,
                'Type': day_type_display,
                'Comments': record.comments if record.comments else "-"
            })
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Display table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # Legend
        st.caption("🔴 = Late arrival (after 9:30 AM) | Overtime is adjusted by admin")
        
        # Add comments/expenses section for today
        self._render_add_comments_expenses(user_id)
    
    def _render_add_comments_expenses(self, user_id: int):
        """
        Render form to add comments and expenses for today.
        
        Args:
            user_id: User ID
        """
        st.markdown("---")
        st.subheader("✏️ Add Today's Information")
        
        # Get today's attendance
        attendance = self.checkin_service.get_today_attendance(user_id)
        
        if not attendance:
            st.info("Check in first to add comments or expenses")
            return
        
        # Create form
        with st.form("add_info_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Comments field
                comments = st.text_area(
                    "Comments",
                    value=attendance.comments if attendance.comments else "",
                    placeholder="Add any notes about today...",
                    height=100
                )
            
            with col2:
                # Expenses field
                expenses = st.number_input(
                    "Extra Expenses (EGP)",
                    min_value=0.0,
                    value=float(attendance.extra_expenses),
                    step=10.0,
                    format="%.2f"
                )
            
            # Submit button
            submitted = st.form_submit_button("💾 Save Information", type="primary")
            
            if submitted:
                # Update comments
                if comments != (attendance.comments or ""):
                    success, msg = self.checkin_service.add_comments(attendance.attendance_id, comments)
                    if success:
                        st.success("Comments saved")
                    else:
                        st.error(f"Failed to save comments: {msg}")
                
                # Update expenses
                if expenses != attendance.extra_expenses:
                    success, msg = self.checkin_service.add_extra_expenses(attendance.attendance_id, expenses)
                    if success:
                        st.success("Expenses saved")
                    else:
                        st.error(f"Failed to save expenses: {msg}")
                
                if comments != (attendance.comments or "") or expenses != attendance.extra_expenses:
                    st.rerun()
    
    def _render_monthly_statistics(self, user_id: int):
        """
        Render monthly statistics summary.
        
        Args:
            user_id: User ID
        """
        st.subheader("📈 This Month's Statistics")
        
        # Get current month report
        today = date.today()
        report = self.report_service.get_monthly_report(user_id, today.year, today.month)
        
        if not report:
            st.info("No data available for this month")
            return
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Working Days", f"{report['actual_working_days']} / {report['expected_working_days']}")
        
        with col2:
            st.metric("Absence Days", report['absence_days'])
        
        with col3:
            st.metric("Total Time", f"{report['working_hours']}h {report['working_minutes']}m")
        
        with col4:
            # Total overtime
            ot_total = report['overtime_minutes']
            if ot_total != 0:
                ot_sign = "+" if ot_total > 0 else ""
                ot_h, ot_m = self.calculator.format_minutes_to_hours_minutes(abs(ot_total))
                st.metric("Total Overtime", f"{ot_sign}{ot_h}h {ot_m}m")
            else:
                st.metric("Total Overtime", "0h 0m")
        
        # Financial summary
        st.markdown("---")
        st.subheader("💰 Financial Summary")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Expenses", CurrencyHelper.format_currency(report['extra_expenses']))
        
        with col2:
            st.metric("Bonus", CurrencyHelper.format_currency(report['bonus']))
            st.caption("Set by admin")
        
        with col3:
            st.metric("Total Salary", CurrencyHelper.format_currency(report['salary']))
        
        # Show calculation breakdown
        with st.expander("📊 Salary Calculation Breakdown"):
            st.write(f"**Total Working Minutes:** {report['total_working_minutes']} minutes")
            st.write(f"**Minute Cost:** {report['minute_cost']} EGP/minute")
            st.write(f"**Base Salary:** {report['total_working_minutes']} × {report['minute_cost']} = "
                    f"{report['total_working_minutes'] * report['minute_cost']:.2f} EGP")
            st.write(f"**Extra Expenses:** {report['extra_expenses']:.2f} EGP")
            st.write(f"**Bonus (admin-set):** {report['bonus']:.2f} EGP")
            st.write(f"**TOTAL:** {report['salary']:.2f} EGP")


def render_employee_dashboard():
    """
    Main function to render employee dashboard.
    
    Called from app.py when employee logs in.
    """
    dashboard = EmployeeDashboard()
    dashboard.render()