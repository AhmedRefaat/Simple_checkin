"""
Admin Dashboard Page
Provides admin interface for managing attendance and employees.

Features:
- View all employees
- Modify attendance records
- Set overtime values
- Set bonus values
- Change day types
- Update employee settings
- Manage holidays
- Generate reports

Usage:
    This module is imported and called by the main app.py
"""

import streamlit as st
from datetime import date, datetime, time
import pandas as pd

from services.admin_service import AdminService
from services.auth_service import AuthService
from services.report_service import ReportService
from services.calculation_service import CalculationService
from utils.helpers import CurrencyHelper
from utils.constants import DayType, UserRole
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class AdminDashboard:
    """
    Admin dashboard interface.
    
    Provides administrators with full control over:
    - Employee management
    - Attendance modifications
    - Overtime and bonus settings
    - Reports and analytics
    """
    
    def __init__(self):
        """Initialize admin dashboard with required services"""
        self.admin_service = AdminService()
        self.auth_service = AuthService()
        self.report_service = ReportService()
        self.calculator = CalculationService()
        logger.debug("AdminDashboard initialized")
    
    def _get_allowed_edit_range(self):
        """
        Calculate the allowed date range for editing overtime/expenses/comments.
        
        Business Rule:
        - If today is between 1st and 8th of current month:
            → Can edit: ALL of previous month + ALL of current month
        - If today is after 8th of current month:
            → Can edit: ALL of current month + Days 1-8 of next month
        
        Returns:
            tuple: (
                first_month_range: tuple(year, month, min_day, max_day) or None,
                second_month_range: tuple(year, month, min_day, max_day)
            )
        
        Examples:
            Today: Oct 25, 2025 (after 8th)
            → Returns: ((2025, 10, 1, 31), (2025, 11, 1, 8))
            → Can edit: All October + Nov 1-8
            
            Today: Nov 5, 2025 (before 9th)
            → Returns: ((2025, 10, 1, 31), (2025, 11, 1, 30))
            → Can edit: All October + All November
            
            Today: Nov 15, 2025 (after 8th)
            → Returns: ((2025, 11, 1, 30), (2025, 12, 1, 8))
            → Can edit: All November + Dec 1-8
        """
        from datetime import timedelta
        from calendar import monthrange
        
        today = date.today()
        current_year = today.year
        current_month = today.month
        current_day = today.day
        
        # Get current month range
        _, last_day_current = monthrange(current_year, current_month)
        current_month_range = (current_year, current_month, 1, last_day_current)
        
        # Determine if we're in the grace period (1st to 8th of month)
        if current_day <= 8:
            # Grace period: Can edit PREVIOUS month (all days) + CURRENT month (all days)
            
            # Calculate previous month
            if current_month == 1:
                prev_year = current_year - 1
                prev_month = 12
            else:
                prev_year = current_year
                prev_month = current_month - 1
            
            _, last_day_prev = monthrange(prev_year, prev_month)
            prev_month_range = (prev_year, prev_month, 1, last_day_prev)
            
            return prev_month_range, current_month_range
        
        else:
            # Regular period: Can edit CURRENT month (all days) + NEXT month (days 1-8)
            
            # Calculate next month
            if current_month == 12:
                next_year = current_year + 1
                next_month = 1
            else:
                next_year = current_year
                next_month = current_month + 1
            
            next_month_range = (next_year, next_month, 1, 8)
            
            return current_month_range, next_month_range

    def _get_allowed_date_range_60days(self):
        """
        Calculate the allowed date range for attendance entries (60 days back).
        
        Returns:
            tuple: (min_date, max_date) - Allowed date range
                min_date: 60 days before today
                max_date: Today
        """
        from datetime import timedelta
        
        today = date.today()
        
        # Min date: 60 days back from today
        min_date = today - timedelta(days=60)
        
        # Max date: Today (cannot add future dates)
        max_date = today
        
        return min_date, max_date
    
    def render(self):
        """
        Render the admin dashboard page.
        
        Main entry point for displaying admin interface.
        """
        logger.info("Rendering admin dashboard")
        
        # Page header
        st.title("🔧 Admin Dashboard")
        st.markdown("**System Administration & Management**")
        st.markdown("---")
        
        # Sidebar for navigation
        page = st.sidebar.selectbox(
            "📋 Select Function",
            [
                "Employee Overview",
                "Add Employee",
                "Quick Add Attendance",
                "Manage Attendance",
                "Set Overtime & Bonus",
                "Employee Settings",
                "Holiday Management",
                "Full Reports",
                "Password Management"  # NEW OPTION defined in branch: feature/change_user_password
            ]
        )
        
        # Render selected page
        if page == "Employee Overview":
            self._render_employee_overview()
        elif page == "Add Employee":
            self._render_add_employee()
        elif page == "Quick Add Attendance":
            self._render_quick_add_attendance()
        elif page == "Manage Attendance":
            self._render_manage_attendance()
        elif page == "Set Overtime & Bonus":
            self._render_overtime_bonus()
        elif page == "Employee Settings":
            self._render_employee_settings()
        elif page == "Holiday Management":
            self._render_holiday_management()
        elif page == "Full Reports":
            self._render_full_reports()
        elif page == "Password Management":  # NEW CONDITION defined in branch: feature/change_user_password
            self._render_password_management()
    
    def _render_employee_overview(self):
        """Render employee overview page"""
        st.header("👥 Employee Overview")
        
        # Get all employees
        employees = self.auth_service.get_all_employees()
        
        if not employees:
            st.info("No employees found")
            return
        
        # Display employee cards
        for emp in employees:
            with st.expander(f"👤 {emp.full_name} (@{emp.username})"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**User ID:** {emp.user_id}")
                    st.write(f"**Join Date:** {emp.join_date}")
                    st.write(f"**Status:** {'✅ Active' if emp.is_active else '❌ Inactive'}")
                
                with col2:
                    st.write(f"**Minute Cost:** {emp.minute_cost} EGP/min")
                    st.write(f"**Vacation Days:** {emp.vacation_days_allowed}")
                
                with col3:
                    # Get current month summary
                    today = date.today()
                    report = self.report_service.get_monthly_report(emp.user_id, today.year, today.month)
                    
                    if report:
                        st.write(f"**This Month:**")
                        st.write(f"Working Days: {report['actual_working_days']}")
                        st.write(f"Salary: {CurrencyHelper.format_currency(report['salary'])}")
    
    def _render_manage_attendance(self):
        """Render attendance management page"""
        st.header("📝 Manage Attendance Records")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
        # Select month
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Get attendance records
        report = self.report_service.get_monthly_report(user_id, year, month)
        
        if not report or not report.get('attendance_records'):
            st.info("No attendance records for this month")
        
        # Always show create form (even if records exist)
        st.markdown("---")
        st.subheader("➕ Create New Record")
        
        # Get allowed date range (60 days back)
        min_date, max_date = self._get_allowed_date_range_60days()
        days_back = (max_date - min_date).days
        
        st.info(f"📅 **Allowed Date Range:** {min_date.strftime('%B %d, %Y')} to {max_date.strftime('%B %d, %Y')} ({days_back} days)")
        
        with st.form("create_attendance"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_date = st.date_input(
                    "Date*", 
                    value=date.today(),
                    min_value=min_date,
                    max_value=max_date,
                    help=f"Select a date within the last {days_back} days"
                )
                check_in = st.time_input(
                    "Check-In Time", 
                    value=None,
                    help="Leave empty if not applicable"
                )
            
            with col2:
                check_out = st.time_input(
                    "Check-Out Time", 
                    value=None,
                    help="Leave empty if not applicable"
                )
                day_type = st.selectbox(
                    "Day Type*", 
                    [dt.value for dt in DayType],
                    help="Type of day (working, vacation, etc.)"
                )
            
            submitted = st.form_submit_button("✅ Create Record", type="primary")
            
            if submitted:
                # Validate date is within range
                if not (min_date <= new_date <= max_date):
                    st.error(f"❌ Date must be between {min_date.strftime('%Y-%m-%d')} and {max_date.strftime('%Y-%m-%d')}")
                else:
                    success, attendance, msg = self.admin_service.create_attendance_record(
                        user_id, new_date, check_in, check_out, day_type
                    )
                    if success:
                        st.success(f"✅ {msg}")
                        # bugfix: remove redundant rerun
                        # part of branch: bug/fix_rerun_issue
                        # st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        
        # If there are existing records, show them below
        if report and report.get('attendance_records'):
            st.markdown("---")
            st.subheader(f"📅 Existing Records: {report['month_name']} {report['year']}")
            
            for record in report['attendance_records']:
                with st.expander(f"📆 {record.attendance_date.strftime('%Y-%m-%d %A')}"):
                    self._render_attendance_editor(record)
            return
    
    def _render_attendance_editor(self, record):
        """
        Render attendance record editor.
        
        Args:
            record: Attendance record object
        """
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Current Values:**")
            st.write(f"Check-In: {record.check_in_time.strftime('%H:%M') if record.check_in_time else 'N/A'}")
            st.write(f"Check-Out: {record.check_out_time.strftime('%H:%M') if record.check_out_time else 'N/A'}")
            st.write(f"Working Time: {record.total_working_minutes} min")
            st.write(f"Overtime: {record.overtime_minutes} min")
            st.write(f"Day Type: {record.day_type}")
            st.write(f"Late: {'Yes' if record.is_late else 'No'}")
        
        with col2:
            st.write("**Modify:**")
            
            # Update times
            with st.form(f"update_times_{record.attendance_id}"):
                new_check_in = st.time_input("New Check-In", value=record.check_in_time)
                new_check_out = st.time_input("New Check-Out", value=record.check_out_time)
                
                if st.form_submit_button("Update Times"):
                    success, msg = self.admin_service.update_check_times(
                        record.attendance_id, new_check_in, new_check_out
                    )
                    if success:
                        st.success(msg)
                        #bugfix: remove redundant rerun 
                        # this fix is part of branch: bug/fix_rerun_issue
                        # st.rerun()
                    else:
                        st.error(msg)
            
            # Update day type
            new_day_type = st.selectbox(
                "Day Type",
                [dt.value for dt in DayType],
                index=[dt.value for dt in DayType].index(record.day_type),
                key=f"daytype_{record.attendance_id}"
            )
            
            if st.button("Update Day Type", key=f"btn_daytype_{record.attendance_id}"):
                success, msg = self.admin_service.change_day_type(record.attendance_id, new_day_type)
                if success:
                    st.success(msg)
                    # bugfix: remove redundant rerun
                    # fix is part of branch: bug/fix_rerun_issue
                    # st.rerun()  # no needed - form submission auto-reruns
                else:
                    st.error(msg)
    
    
    # ======================= Adjust the method to include the overtime, expense, comment per day =======================   
    # this change is added as part of branch: bug/fix_overtime_issue.
    def _render_overtime_bonus(self):
        """Render daily adjustments (overtime, expenses, comments) and bonus management page"""
        st.header("📝 Daily Adjustments & Bonus")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
        # Two tabs: Daily Adjustments and Monthly Bonus
        tab1, tab2 = st.tabs(["📝 Daily Adjustments (Overtime, Expenses & Comments)", "💰 Monthly Bonus"])
        
        with tab1:
            self._render_daily_adjustments(user_id)
        
        with tab2:
            self._render_bonus_setter(user_id)

    # ======================= New methods for daily adjustments =======================
    # Render daily adjustments: overtime, expenses, and comments in one unified view.
    # this is added as part of branch: bug/fix_overtime_issue.
    
    def _render_daily_adjustments(self, user_id: int):
        """
        Render daily adjustments: overtime, expenses, and comments in one unified view.
        Admin can edit current month + first 8 days of next month.
        
        Args:
            user_id: User ID
        """
        st.subheader("Daily Adjustments: Overtime, Expenses & Comments")
        st.info("ℹ️ **Overtime**: Time adjustment (± minutes) | **Expenses**: Additional costs (EGP) | **Comment**: Reason/notes for adjustments")
        st.info("ℹ️ **Overtime**, **Expenses**, **Comment**: are editable up to 8th of the next month ONLY!")
        
        # Get allowed edit range
        first_range, second_range = self._get_allowed_edit_range()

        # Display allowed range with clear messaging
        first_month_name = date(first_range[0], first_range[1], 1).strftime('%B %Y')
        second_month_name = date(second_range[0], second_range[1], 1).strftime('%B %Y')

        # Determine message based on date range
        today = date.today()
        if today.day <= 8:
            # Grace period message
            st.success(f"✅ **Editable Period (Grace Period):** All of {first_month_name} + All of {second_month_name}")
            st.info(f"📅 You're in the grace period (1st-8th). You can edit previous and current month records.")
        else:
            # Regular period message
            st.success(f"✅ **Editable Period:** All of {first_month_name} + {second_month_name} (days 1-8)")
            st.info(f"📅 Starting from 9th, you can only edit current month + first 8 days of next month.")
        
        # Get attendance records for both months
        all_records = []
        today = date.today()

        # First month records (always all days)
        first_report = self.report_service.get_monthly_report(user_id, first_range[0], first_range[1])
        if first_report and first_report.get('attendance_records'):
            all_records.extend([
                (record, first_month_name) 
                for record in first_report['attendance_records']
            ])

        # Second month records (filter based on grace period)
        second_report = self.report_service.get_monthly_report(user_id, second_range[0], second_range[1])
        if second_report and second_report.get('attendance_records'):
            if today.day <= 8:
                # Grace period: Show ALL days of second month (current month)
                all_records.extend([
                    (record, second_month_name) 
                    for record in second_report['attendance_records']
                ])
            else:
                # Regular period: Show only days 1-8 of second month (next month)
                all_records.extend([
                    (record, second_month_name) 
                    for record in second_report['attendance_records']
                    if record.attendance_date.day <= 8
                ])
        
        if not all_records:
            st.info("No attendance records found in the editable period")
            return
        
       # Group records by month for better organization
        st.markdown("---")

        first_month_records = [(r, m) for r, m in all_records if m == first_month_name]
        second_month_records = [(r, m) for r, m in all_records if m == second_month_name]

        # Render first month
        if first_month_records:
            st.subheader(f"📅 {first_month_name}")
            for record, _ in first_month_records:
                self._render_daily_adjustment_row(record)

        # Render second month
        if second_month_records:
            st.markdown("---")
            # Dynamic heading based on grace period
            if today.day <= 8:
                st.subheader(f"📅 {second_month_name} (Current Month - All Days)")
            else:
                st.subheader(f"📅 {second_month_name} (Days 1-8 only)")
            
            for record, _ in second_month_records:
                self._render_daily_adjustment_row(record)

    # ======================= New methods for daily adjustments in row view (clean UI) =======================
    # this is added as part of branch: bug/fix_overtime_issue.
    def _render_daily_adjustment_row(self, record):
        """
        Render a single row for editing overtime, expenses, and comments together.
        Uses an expander to keep the UI clean while allowing detailed editing.
        
        Args:
            record: Attendance record object
        """
        # Build expander title with current values summary
        date_str = record.attendance_date.strftime('%Y-%m-%d %A')
        worked_str = f"{record.total_working_minutes} min"
        
        # Show indicators if there are adjustments
        indicators = []
        if record.overtime_minutes != 0:
            indicators.append(f"⏱️ OT: {record.overtime_minutes:+d} min")
        if record.extra_expenses != 0:
            indicators.append(f"💰 Exp: {record.extra_expenses:.0f} EGP")
        if record.comments:
            indicators.append(f"💬 Has comment")
        
        title = f"📆 {date_str} | Worked: {worked_str}"
        if indicators:
            title += f" | {' | '.join(indicators)}"
        
        with st.expander(title, expanded=False):
            # Display basic info
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.caption(f"**Day Type:** {record.day_type}")
                st.caption(f"**Check-In:** {record.check_in_time.strftime('%H:%M') if record.check_in_time else 'N/A'}")
            with col_info2:
                st.caption(f"**Late:** {'Yes ⚠️' if record.is_late else 'No ✅'}")
                st.caption(f"**Check-Out:** {record.check_out_time.strftime('%H:%M') if record.check_out_time else 'N/A'}")
            
            st.markdown("---")
            
            # Adjustments form
            col1, col2 = st.columns(2)
            
            with col1:
                new_overtime = st.number_input(
                    "⏱️ Overtime (minutes)",
                    value=record.overtime_minutes,
                    step=10,
                    key=f"ot_{record.attendance_id}",
                    help="Positive = bonus time, Negative = penalty"
                )
            
            with col2:
                new_expenses = st.number_input(
                    "💰 Extra Expenses (EGP)",
                    value=record.extra_expenses,
                    step=10.0,
                    format="%.2f",
                    key=f"exp_{record.attendance_id}",
                    help="Additional expenses (taxi, meals, etc.)"
                )
            
            # Comment field (full width)
            current_comment = record.comments or ""
            new_comment = st.text_area(
                "💬 Comment / Reason",
                value=current_comment,
                height=80,
                placeholder="Add notes explaining why overtime/expenses were added (e.g., 'Stayed late for urgent client meeting', 'Taxi fare to client site')...",
                key=f"comment_{record.attendance_id}",
                help="Document the reason for adjustments"
            )
            
            # ✅ FIX: Calculate change flags BEFORE button, so they're available in entire scope
            overtime_changed = new_overtime != record.overtime_minutes
            expenses_changed = new_expenses != record.extra_expenses
            comment_changed = new_comment.strip() != current_comment.strip()
            
            # Save button
            # bugfix for removing st.rerun() after save - part of branch: bug/fix_absence_Days_slary_calculations
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                save_clicked = st.button("💾 Save All", key=f"btn_save_{record.attendance_id}", type="primary")

            # ✅ FIX: Process button click outside the column context
            if save_clicked:
                # Check if any values changed
                if not overtime_changed and not expenses_changed and not comment_changed:
                    st.info("ℹ️ No changes detected")
                else:
                    # Update all three fields at once
                    success, msg = self.admin_service.update_daily_adjustments(
                        record.attendance_id,
                        new_overtime,
                        new_expenses,
                        new_comment.strip() if new_comment.strip() else None
                    )
                    
                    if success:
                        st.success(f"✅ {msg}")
                        # ✅ NO st.rerun() needed - button click auto-reruns
                    else:
                        st.error(f"❌ {msg}")
            
            with col_btn2:
                # Show what will be updated (now variables are in scope!)
                changes = []
                if overtime_changed:
                    changes.append(f"Overtime: {record.overtime_minutes} → {new_overtime}")
                if expenses_changed:
                    changes.append(f"Expenses: {record.extra_expenses:.0f} → {new_expenses:.0f} EGP")
                if comment_changed:
                    changes.append("Comment: Updated")
                
                if changes:
                    st.caption("📝 Changes: " + " | ".join(changes))
    
    def _render_bonus_setter(self, user_id: int):
        """
        Render monthly bonus setter.
        
        Args:
            user_id: User ID
        """
        st.subheader("Set Monthly Bonus")
        st.info("ℹ️ Bonus is a fixed amount (EGP) added to monthly salary, independent of overtime")
        
        # Select month
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year, key="bonus_year")
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month, key="bonus_month")
        
        # Get current bonus
        report = self.report_service.get_monthly_report(user_id, year, month)
        current_bonus = report.get('bonus', 0.0) if report else 0.0
        
        # Bonus input
        st.write(f"**Current Bonus:** {CurrencyHelper.format_currency(current_bonus)}")
        
        with st.form("set_bonus_form"):
            new_bonus = st.number_input(
                "New Bonus Amount (EGP)",
                value=current_bonus,
                step=100.0,
                format="%.2f",
                help="Enter bonus amount. Can be positive or negative."
            )
            
            submitted = st.form_submit_button("💾 Set Bonus")
    
        # ✅ FIX: Process form submission OUTSIDE the form block
        # Fix the auto-refresh issue after submission
        #part of the branch: bug/fix_absence_salary_calculation
        if submitted:
            success, msg = self.admin_service.update_bonus(user_id, year, month, new_bonus)
            if success:
                st.success(msg)
                # ✅ NO st.rerun() needed - form submission auto-reruns
            else:
                st.error(msg)
    
    def _render_employee_settings(self):
        """Render employee settings page"""
        st.header("⚙️ Employee Settings")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
        # Get employee details
        employee = self.auth_service.get_user_by_id(user_id)
        
        if not employee:
            st.error("Employee not found")
            return
        
        # Display and edit settings
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Minute Cost")
            st.write(f"**Current:** {employee.minute_cost} EGP/minute")
            
            with st.form("update_minute_cost"):
                new_cost = st.number_input(
                    "New Minute Cost (EGP)",
                    min_value=0.0,
                    value=employee.minute_cost,
                    step=0.5,
                    format="%.2f"
                )
                
                if st.form_submit_button("Update Minute Cost"):
                    success, msg = self.admin_service.update_minute_cost(user_id, new_cost)
                    if success:
                        st.success(msg)
                        # bugfix: remove redundant rerun
                        # part of branch: bug/fix_rerun_issue
                        #st.rerun()
                    else:
                        st.error(msg)
        
        with col2:
            st.subheader("🏖️ Vacation Days")
            st.write(f"**Current:** {employee.vacation_days_allowed} days/year")
            
            with st.form("update_vacation_days"):
                new_days = st.number_input(
                    "New Vacation Days",
                    min_value=0,
                    value=employee.vacation_days_allowed,
                    step=1
                )
                
                if st.form_submit_button("Update Vacation Days"):
                    success, msg = self.admin_service.update_vacation_allowance(user_id, new_days)
                    if success:
                        st.success(msg)
                        # bugfix: remove redundant rerun for updating employee_vacation balance
                        # part of branch: bug/fix_rerun_issue
                        # st.rerun()
                    else:
                        st.error(msg)
    
    def _render_holiday_management(self):
        """Render holiday management page"""
        st.header("📆 Holiday Management")
        
        # Get all holidays
        holidays = self.calculator.get_all_holidays()
        
        # Display holidays
        st.subheader("Current Holidays")
        
        if holidays:
            for holiday in holidays:
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**{holiday.holiday_date.strftime('%Y-%m-%d')}**")
                
                with col2:
                    st.write(holiday.holiday_name)
                
                with col3:
                    if st.button("🗑️ Remove", key=f"remove_{holiday.holiday_id}"):
                        success, msg = self.admin_service.remove_holiday(holiday.holiday_date)
                        if success:
                            st.success(msg)
                            # bugfix: remove redundant rerun
                            # part of branch: bug/fix_rerun_issue
                            # st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("No holidays defined")
        
        # Add new holiday
        st.markdown("---")
        st.subheader("➕ Add New Holiday")
        
        with st.form("add_holiday_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                holiday_date = st.date_input("Date", value=date.today())
            
            with col2:
                holiday_name = st.text_input("Holiday Name", placeholder="e.g., National Day")
            
            if st.form_submit_button("Add Holiday"):
                if holiday_name:
                    success, msg = self.admin_service.add_holiday(holiday_date, holiday_name)
                    if success:
                        st.success(msg)
                        # bugfix: remove redundant rerun
                        # part of branch: bug/fix_rerun_issue
                        # st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter holiday name")
    
    def _render_full_reports(self):
        """Render full reports page"""
        st.header("📊 Full Reports")
        
        # Report type selector
        report_type = st.radio(
            "Report Type",
            ["Single Employee", "All Employees"],
            horizontal=True
        )
        
        if report_type == "Single Employee":
            self._render_single_employee_report()
        else:
            self._render_all_employees_report()
    
    def _render_single_employee_report(self):
        """Render single employee full report"""
        st.subheader("👤 Employee Full Report")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
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
        st.subheader("📈 Cumulative Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Working Days", report['cumulative_stats']['total_working_days'])
        with col2:
            st.metric("Total Hours", report['cumulative_stats']['total_working_hours'])
        with col3:
            st.metric("Total Bonus", CurrencyHelper.format_currency(report['cumulative_stats']['total_bonus']))
        with col4:
            st.metric("Total Salary", CurrencyHelper.format_currency(report['cumulative_stats']['total_salary']))
        
        # Display monthly summaries table
        st.markdown("---")
        st.subheader("📅 Monthly Breakdown")
        
        if report['monthly_summaries']:
            data = []
            for summary in report['monthly_summaries']:
                data.append({
                    'Month': f"{summary['month_name']} {summary['year']}",
                    'Working Days': summary['working_days'],
                    'Absence Days': summary['absence_days'],
                    'Working Time (Hrs)': summary['working_hours'],
                    'Working Time (Min)': summary['working_minutes'],
                    'Total (min)': summary['total_minutes'],
                    'Overtime (min)': summary['overtime_minutes'],
                    'Minute Price (EGP)': report['minute_cost'],
                    'Bonus (EGP)': f"{summary['bonus']:.2f}",
                    'Salary (EGP)': f"{summary['salary']:.2f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No monthly data available")
    
    def _render_all_employees_report(self):
        """Render all employees report"""
        st.subheader("👥 All Employees Report")
        
        # Select month
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Get reports for all employees
        reports = self.report_service.get_all_employees_report(year, month)
        
        if not reports:
            st.info("No data available")
            return
        
        # Create summary table
        data = []
        for report in reports:
            data.append({
                'Employee': report['user_name'],
                'Working Days': report['actual_working_days'],
                'Absence Days': report['absence_days'],
                'Total Hours': report['working_hours'],
                'Total Minutes': report['working_minutes'],
                'Overtime (min)': report['overtime_minutes'],
                'Expenses (EGP)': f"{report['extra_expenses']:.2f}",
                'Bonus (EGP)': f"{report['bonus']:.2f}",
                'Salary (EGP)': f"{report['salary']:.2f}"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Summary totals
        st.markdown("---")
        st.subheader("💰 Totals")
        
        total_salary = sum(r['salary'] for r in reports)
        total_bonus = sum(r['bonus'] for r in reports)
        total_expenses = sum(r['extra_expenses'] for r in reports)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", CurrencyHelper.format_currency(total_expenses))
        with col2:
            st.metric("Total Bonus", CurrencyHelper.format_currency(total_bonus))
        with col3:
            st.metric("Total Salary", CurrencyHelper.format_currency(total_salary))
    
    
    def _render_add_employee(self):
        """Render add new employee form"""
        st.subheader("➕ Add New Employee")
        
        with st.form("add_employee_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                #bugfix: username must be lowercase
                username = st.text_input("Username*", placeholder="e.g., john_doe", help="username is case-sensitive and will be converted to lowercase")
                password = st.text_input("Password*", type="password", placeholder="Minimum 6 characters")
                full_name = st.text_input("Full Name*", placeholder="e.g., John Doe")
            
            with col2:
                minute_cost = st.number_input("Minute Cost (EGP)*", min_value=0.0, value=5.0, step=0.5)
                vacation_days = st.number_input("Vacation Days Allowed", min_value=0, value=21, step=1)
                join_date = st.date_input("Join Date", value=date.today())
            
            submitted = st.form_submit_button("➕ Create Employee", type="primary")
            
            if submitted:
                if not username or not password or not full_name:
                    st.error("Username, Password, and Full Name are required!")
                else:
                    # Create employee
                    success, user, message = self.auth_service.create_user(
                        username=username,
                        password=password,
                        full_name=full_name,
                        role=UserRole.EMPLOYEE.value,
                        minute_cost=minute_cost,
                        vacation_days=vacation_days,
                        join_date=join_date
                    )
                    
                    if success:
                        st.success(f"✓ Employee '{full_name}' created successfully!")
                        st.info(f"Login credentials:\nUsername: {username}\nPassword: {password}")
                    else:
                        st.error(f"✗ Failed to create employee: {message}")

    def _render_quick_add_attendance(self):
        """Render quick attendance entry page with 60-day lookback"""
        st.header("⚡ Quick Add Attendance")
        
        # Get allowed date range
        min_date, max_date = self._get_allowed_date_range_60days()
        days_back = (max_date - min_date).days
        
        # Display date range info prominently
        st.success(f"✅ **You can add attendance for the last {days_back} days**")
        st.info(f"📅 Date Range: **{min_date.strftime('%B %d, %Y')}** to **{max_date.strftime('%B %d, %Y')}**")
        
        # Get all employees
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("⚠️ No employees found. Please add employees first.")
            return
        
        # Create form
        with st.form("quick_add_attendance_form", clear_on_submit=True):
            st.subheader("📝 Attendance Entry")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Employee selection
                emp_options = {f"{e.full_name} (@{e.username})": e.user_id for e in employees}
                selected_emp = st.selectbox(
                    "Select Employee*",
                    list(emp_options.keys()),
                    help="Choose the employee for this attendance entry"
                )
                user_id = emp_options[selected_emp]
                
                # Date selection with validation
                attendance_date = st.date_input(
                    "Date*",
                    value=date.today(),
                    min_value=min_date,
                    max_value=max_date,
                    help=f"Must be within the last {days_back} days"
                )
                
                # Day type
                day_type = st.selectbox(
                    "Day Type*",
                    [dt.value for dt in DayType],
                    help="Select the type of day"
                )
            
            with col2:
                # Check-in time
                check_in = st.time_input(
                    "Check-In Time",
                    value=None,
                    help="Leave empty if employee didn't check in"
                )
                
                # Check-out time
                check_out = st.time_input(
                    "Check-Out Time",
                    value=None,
                    help="Leave empty if employee didn't check out"
                )
                
                # Note about overtime/bonus
                st.caption("💡 **Note:** Overtime and bonus are set separately in their dedicated sections")
            
            # Submit button
            submitted = st.form_submit_button("✅ Create Attendance Record", type="primary", use_container_width=True)
            
            if submitted:
                # Validate date is within range (double-check)
                if not (min_date <= attendance_date <= max_date):
                    st.error(f"❌ Date must be between {min_date.strftime('%Y-%m-%d')} and {max_date.strftime('%Y-%m-%d')}")
                else:
                    # Create attendance record
                    success, attendance, msg = self.admin_service.create_attendance_record(
                        user_id, attendance_date, check_in, check_out, day_type
                    )
                    
                    if success:
                        st.success(f"✅ {msg}")
                        st.balloons()
                        
                        # Show created record details
                        with st.container():
                            st.markdown("---")
                            st.subheader("📋 Created Record Details")
                            
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.metric("Employee", selected_emp.split('(')[0].strip())
                            with col_b:
                                st.metric("Date", attendance_date.strftime('%Y-%m-%d'))
                            with col_c:
                                st.metric("Day Type", day_type)
                            
                            if check_in or check_out:
                                col_d, col_e = st.columns(2)
                                with col_d:
                                    if check_in:
                                        st.write(f"**Check-In:** {check_in.strftime('%H:%M')}")
                                with col_e:
                                    if check_out:
                                        st.write(f"**Check-Out:** {check_out.strftime('%H:%M')}")
                    else:
                        st.error(f"❌ {msg}")
        
        # Show recent entries summary
        st.markdown("---")
        st.subheader("📊 Recent Entries (Current Month)")
        
        # Get current month attendance for all employees
        today = date.today()
        all_reports = self.report_service.get_all_employees_report(today.year, today.month)
        
        if all_reports:
            summary_data = []
            for report in all_reports:
                summary_data.append({
                    'Employee': report['user_name'],
                    'Working Days': report['actual_working_days'],
                    'Absence Days': report['absence_days'],
                    'Total Hours': f"{report['working_hours']:.1f}"
                })
            
            df = pd.DataFrame(summary_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No attendance records for current month yet")

    # ================== Change Password feature methods (admin or Employee-password-reset) =======================
    # The admin can change their own password or reset any employee's password without knowing their current password
    # this implementation is part of branch: feature/change_user_password

    def _render_password_management(self):
        """Render password management page for admin"""
        st.header("🔐 Password Management")
        
        # Two tabs: Change own password & Reset employee password
        tab1, tab2 = st.tabs(["🔒 Change My Password", "🔑 Reset Employee Password"])
        
        with tab1:
            st.subheader("Change Admin Password")
            st.info("ℹ️ Change your own admin account password")
            
            with st.form("admin_change_password_form"):
                current_password = st.text_input(
                    "Current Password*",
                    type="password",
                    placeholder="Enter your current password",
                    key="admin_current"
                )
                
                new_password = st.text_input(
                    "New Password*",
                    type="password",
                    placeholder="Enter new password (min 6 characters)",
                    key="admin_new"
                )
                
                confirm_password = st.text_input(
                    "Confirm New Password*",
                    type="password",
                    placeholder="Re-enter new password",
                    key="admin_confirm"
                )
                
                submitted = st.form_submit_button("🔒 Change My Password", type="primary")
                
                if submitted:
                    # Get current admin user ID from session
                    admin_user_id = st.session_state.user['user_id']
                    
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
                            admin_user_id,
                            current_password,
                            new_password
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info("🔄 Please log out and log in again with your new password")
                        else:
                            st.error(f"❌ {message}")
        
        with tab2:
            st.subheader("Reset Employee Password")
            st.warning("⚠️ Admin privilege: Reset any employee's password without knowing their current password")
            
            # Select employee
            employees = self.auth_service.get_all_employees()
            if not employees:
                st.info("No employees found")
                return
            
            emp_options = {f"{e.full_name} (@{e.username})": e.user_id for e in employees}
            selected_emp = st.selectbox("Select Employee*", list(emp_options.keys()))
            user_id = emp_options[selected_emp]
            
            with st.form("admin_reset_password_form"):
                new_password = st.text_input(
                    "New Password*",
                    type="password",
                    placeholder="Enter new password for employee (min 6 characters)",
                    key="reset_new"
                )
                
                confirm_password = st.text_input(
                    "Confirm New Password*",
                    type="password",
                    placeholder="Re-enter new password",
                    key="reset_confirm"
                )
                
                submitted = st.form_submit_button("🔑 Reset Password", type="primary")
                
                if submitted:
                    # Validation
                    if not new_password or not confirm_password:
                        st.error("❌ All fields are required")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match")
                    elif len(new_password) < 6:
                        st.error("❌ Password must be at least 6 characters long")
                    else:
                        # Call admin service to reset password
                        success, message = self.admin_service.reset_user_password(
                            user_id,
                            new_password
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.info(f"🔔 Please inform the employee of their new password: `{new_password}`")
                        else:
                            st.error(f"❌ {message}")

def render_admin_dashboard():
    """
    Main function to render admin dashboard.
    
    Called from app.py when admin logs in.
    """
    dashboard = AdminDashboard()
    dashboard.render()