"""
Reports Page
Provides detailed reporting interface for both employees and admins.

Features:
- Monthly reports with detailed breakdown
- Full employment history
- Export capabilities
- Visual statistics
- Comparative analysis

Usage:
    This module is imported and called by the main app.py
"""

import streamlit as st
from datetime import date, datetime
import pandas as pd

from services.report_service import ReportService
from services.auth_service import AuthService
from services.calculation_service import CalculationService
from utils.helpers import CurrencyHelper
from utils.constants import SessionKeys, UserRole
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ReportsPage:
    """
    Reports page interface.
    
    Provides comprehensive reporting functionality for:
    - Monthly attendance reports
    - Full employment history
    - Financial summaries
    - Data export
    """
    
    def __init__(self):
        """Initialize reports page with required services"""
        self.report_service = ReportService()
        self.auth_service = AuthService()
        self.calculator = CalculationService()
        logger.debug("ReportsPage initialized")
    
    def render(self):
        """
        Render the reports page.
        
        Main entry point for displaying reports interface.
        """
        logger.info("Rendering reports page")
        
        # Page header
        st.title("📊 Reports & Analytics")
        st.markdown("**Comprehensive Attendance & Salary Reports**")
        st.markdown("---")
        
        # Get user info from session
        user_id = st.session_state.get(SessionKeys.USER_ID.value)
        user_role = st.session_state.get(SessionKeys.ROLE.value)
        
        if not user_id:
            st.error("Session expired. Please log in again.")
            return
        
        # Different interfaces for employee vs admin
        if user_role == UserRole.ADMIN.value:
            self._render_admin_reports()
        else:
            self._render_employee_reports(user_id)
    
    def _render_employee_reports(self, user_id: int):
        """
        Render employee reports interface.
        
        Args:
            user_id: User ID
        """
        st.subheader("📈 Your Reports")
        
        # Report type selector
        report_type = st.radio(
            "Select Report Type",
            ["Monthly Report", "Full Employment History"],
            horizontal=True
        )
        
        if report_type == "Monthly Report":
            self._render_monthly_report_employee(user_id)
        else:
            self._render_full_history_employee(user_id)
    
    def _render_monthly_report_employee(self, user_id: int):
        """
        Render monthly report for employee.
        
        Args:
            user_id: User ID
        """
        st.subheader("📅 Monthly Attendance Report")
        
        # Month selector
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Generate report button
        if st.button("📊 Generate Report", type="primary"):
            self._display_monthly_report(user_id, year, month)
    
    def _render_full_history_employee(self, user_id: int):
        """
        Render full employment history for employee.
        
        Args:
            user_id: User ID
        """
        st.subheader("📜 Full Employment History")
        
        # Generate report button
        if st.button("📊 Generate Full Report", type="primary"):
            self._display_full_report(user_id)
    
    def _render_admin_reports(self):
        """Render admin reports interface"""
        st.subheader("🔧 Admin Reports")
        
        # Report type selector
        report_type = st.selectbox(
            "Select Report Type",
            [
                "Single Employee - Monthly",
                "Single Employee - Full History",
                "All Employees - Monthly",
                "All Employees - Comparison"
            ]
        )
        
        if report_type == "Single Employee - Monthly":
            self._render_single_employee_monthly()
        elif report_type == "Single Employee - Full History":
            self._render_single_employee_full()
        elif report_type == "All Employees - Monthly":
            self._render_all_employees_monthly()
        else:
            self._render_all_employees_comparison()
    
    def _render_single_employee_monthly(self):
        """Render single employee monthly report for admin"""
        st.subheader("👤 Employee Monthly Report")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
        # Month selector
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Generate report
        if st.button("📊 Generate Report", type="primary"):
            self._display_monthly_report(user_id, year, month)
    
    def _render_single_employee_full(self):
        """Render single employee full history for admin"""
        st.subheader("👤 Employee Full History")
        
        # Select employee
        employees = self.auth_service.get_all_employees()
        if not employees:
            st.warning("No employees found")
            return
        
        emp_options = {f"{e.full_name} ({e.username})": e.user_id for e in employees}
        selected_emp = st.selectbox("Select Employee", list(emp_options.keys()))
        user_id = emp_options[selected_emp]
        
        # Generate report
        if st.button("📊 Generate Full Report", type="primary"):
            self._display_full_report(user_id)
    
    def _render_all_employees_monthly(self):
        """Render all employees monthly report"""
        st.subheader("👥 All Employees Monthly Report")
        
        # Month selector
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Generate report
        if st.button("📊 Generate Report", type="primary"):
            self._display_all_employees_monthly(year, month)
    
    def _render_all_employees_comparison(self):
        """Render all employees comparison report"""
        st.subheader("📊 Employee Comparison Report")
        
        # Month selector
        col1, col2 = st.columns(2)
        with col1:
            year = st.number_input("Year", min_value=2020, max_value=2100, value=date.today().year)
        with col2:
            month = st.number_input("Month", min_value=1, max_value=12, value=date.today().month)
        
        # Generate report
        if st.button("📊 Generate Comparison", type="primary"):
            self._display_employee_comparison(year, month)
    
    # ==================== Report Display Methods ====================
    
    def _display_monthly_report(self, user_id: int, year: int, month: int):
        """
        Display monthly report with detailed breakdown.
        
        Args:
            user_id: User ID
            year: Year
            month: Month
        """
        logger.info(f"Displaying monthly report for user {user_id}: {year}-{month:02d}")
        
        # Get report data
        report = self.report_service.get_monthly_report(user_id, year, month)
        
        if not report:
            st.error("No data available for this period")
            return
        
        # Display header
        st.markdown("---")
        st.header(f"📅 {report['month_name']} {report['year']}")
        st.write(f"**Employee:** {report['user_name']}")
        
        # Summary metrics
        st.subheader("📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Working Days",
                f"{report['actual_working_days']} / {report['expected_working_days']}"
            )
        
        with col2:
            st.metric("Absence Days", report['absence_days'])
        
        with col3:
            st.metric(
                "Total Time",
                f"{report['working_hours']}h {report['working_minutes']}m"
            )
        
        with col4:

            ot_total = report['overtime_minutes']
            #bugfix: show sign for overtime as (+/-) based on value
            # fix is part of branch: bug/fix_absence_fays_salary_calculations
            ot_sign = "+" if ot_total > 0 else "-"
            ot_h, ot_m = self.calculator.format_minutes_to_hours_minutes(abs(ot_total))
            st.metric("Total Overtime", f"{ot_sign}{ot_h}h {ot_m}m")
        
        # Financial breakdown
        st.subheader("💰 Financial Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Minute Cost", f"{report['minute_cost']} EGP/min")
        
        with col2:
            st.metric("Extra Expenses", CurrencyHelper.format_currency(report['extra_expenses']))
        
        with col3:
            st.metric("Bonus", CurrencyHelper.format_currency(report['bonus']))
        
        with col4:
            st.metric("Total Salary", CurrencyHelper.format_currency(report['salary']))
        
        # Detailed calculation
        with st.expander("🔍 Detailed Salary Calculation"):
            #bugfix: include overtime minutes in salary breakdown display
            # fix is part of branch: bug/fix_absence_fays_salary_calculations
            st.write("**Formula:** Salary = ((Total Working Minutes + Overtime Minutes) × Minute Cost) + Extra Expenses + Bonus")
            st.write("")
            st.write(f"**Total Working Minutes:** {report['total_working_minutes']} minutes")
            #Include overtime minutes in breakdown
            #fix is part of branch: bug/fix_absence_fays_salary_calculations
            st.write(f"**Overtime Minutes:** {report['overtime_minutes']} minutes")
            st.write(f"**Minute Cost:** {report['minute_cost']} EGP/minute")
            #bugfix: include overtime minutes in salary breakdown display and make it more clear
            # fix is part of branch: bug/fix_absence_fays_salary_calculations
            st.write(f"**Base Salary:** {(report['total_working_minutes'] + report['overtime_minutes'])} × {report['minute_cost']} = "
                    f"{(report['total_working_minutes'] + report['overtime_minutes']) * report['minute_cost']:.2f} EGP")
            st.write(f"**Extra Expenses:** +{report['extra_expenses']:.2f} EGP")
            st.write(f"**Bonus (admin-set):** +{report['bonus']:.2f} EGP")
            st.write(f"**TOTAL SALARY:** {report['salary']:.2f} EGP")
        
        # Attendance records table
        st.subheader("📋 Daily Attendance Records")
        
        if report['attendance_records']:
            data = []
            for record in report['attendance_records']:
                # Format data
                check_in = record.check_in_time.strftime('%H:%M') if record.check_in_time else "-"
                check_out = record.check_out_time.strftime('%H:%M') if record.check_out_time else "-"
                
                hours, mins = self.calculator.format_minutes_to_hours_minutes(record.total_working_minutes)
                working_time = f"{hours}h {mins}m" if record.total_working_minutes > 0 else "-"
                
                ot_sign = "+" if record.overtime_minutes > 0 else ""
                overtime_str = f"{ot_sign}{record.overtime_minutes}" if record.overtime_minutes != 0 else "0"
                
                late_flag = "🔴" if record.is_late else ""
                
                data.append({
                    'Date': record.attendance_date.strftime('%Y-%m-%d'),
                    'Day': record.attendance_date.strftime('%A'),
                    'Check-In': f"{late_flag} {check_in}".strip(),
                    'Check-Out': check_out,
                    'Working Time': working_time,
                    'Overtime (min)': overtime_str,
                    'Expenses (EGP)': f"{record.extra_expenses:.2f}" if record.extra_expenses > 0 else "-",
                    'Type': record.day_type.replace('_', ' ').title(),
                    'Comments': record.comments if record.comments else "-"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.caption("🔴 = Late arrival (after 9:30 AM)")
        else:
            st.info("No attendance records for this period")
    
    def _display_full_report(self, user_id: int):
        """
        Display full employment history report.
        
        Args:
            user_id: User ID
        """
        logger.info(f"Displaying full report for user {user_id}")
        
        # Get report data
        report = self.report_service.get_full_report(user_id)
        
        if not report:
            st.error("No data available")
            return
        
        # Display header
        st.markdown("---")
        st.header(f"📜 Full Employment History")
        st.write(f"**Employee:** {report['user_name']}")
        st.write(f"**Join Date:** {report['join_date']}")
        st.write(f"**Minute Cost:** {report['minute_cost']} EGP/minute")
        st.write(f"**Vacation Days Allowed:** {report['vacation_days_allowed']} days/year")
        
        # Cumulative statistics
        st.subheader("📈 Cumulative Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Working Days", report['cumulative_stats']['total_working_days'])
            st.metric("Total Absence Days", report['cumulative_stats']['total_absence_days'])
        
        with col2:
            st.metric(
                "Total Working Time",
                f"{report['cumulative_stats']['total_working_hours']}h "
                f"{report['cumulative_stats']['total_working_minutes']}m"
            )
            st.metric("Total Overtime", f"{report['cumulative_stats']['total_overtime_minutes']} min")
        
        with col3:
            st.metric("Total Bonus", CurrencyHelper.format_currency(report['cumulative_stats']['total_bonus']))
            st.metric("Total Salary", CurrencyHelper.format_currency(report['cumulative_stats']['total_salary']))
        
        # Monthly summaries table
        st.subheader("📅 Monthly Breakdown")
        
        if report['monthly_summaries']:
            data = []
            for summary in report['monthly_summaries']:
                data.append({
                    'Month': f"{summary['month_name']} {summary['year']}",
                    'Working Days': summary['working_days'],
                    'Absence Days': summary['absence_days'],
                    'Working Hrs': summary['working_hours'],
                    'Working Min': summary['working_minutes'],
                    'Total (min)': summary['total_minutes'],
                    'Overtime (min)': summary['overtime_minutes'],
                    'Min Price (EGP)': report['minute_cost'],
                    'Bonus (EGP)': f"{summary['bonus']:.2f}",
                    'Salary (EGP)': f"{summary['salary']:.2f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export option
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"employment_history_{report['user_name']}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No monthly data available")
    
    def _display_all_employees_monthly(self, year: int, month: int):
        """
        Display monthly report for all employees.
        
        Args:
            year: Year
            month: Month
        """
        logger.info(f"Displaying all employees monthly report: {year}-{month:02d}")
        
        # Get reports
        reports = self.report_service.get_all_employees_report(year, month)
        
        if not reports:
            st.error("No data available")
            return
        
        # Display header
        st.markdown("---")
        month_name = self.calculator.get_month_name(month)
        st.header(f"👥 All Employees - {month_name} {year}")
        
        # Create summary table
        data = []
        total_salary = 0
        total_bonus = 0
        total_expenses = 0
        
        for report in reports:
            data.append({
                'Employee': report['user_name'],
                'Working Days': f"{report['actual_working_days']}/{report['expected_working_days']}",
                'Absence': report['absence_days'],
                'Hours': report['working_hours'],
                'Minutes': report['working_minutes'],
                'Overtime (min)': report['overtime_minutes'],
                'Expenses (EGP)': f"{report['extra_expenses']:.2f}",
                'Bonus (EGP)': f"{report['bonus']:.2f}",
                'Salary (EGP)': f"{report['salary']:.2f}"
            })
            
            total_salary += report['salary']
            total_bonus += report['bonus']
            total_expenses += report['extra_expenses']
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Totals summary
        st.markdown("---")
        st.subheader("💰 Totals")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Employees", len(reports))
        
        with col2:
            st.metric("Total Expenses", CurrencyHelper.format_currency(total_expenses))
        
        with col3:
            st.metric("Total Bonus", CurrencyHelper.format_currency(total_bonus))
        
        with col4:
            st.metric("Total Salary", CurrencyHelper.format_currency(total_salary))
        
        # Export option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"all_employees_{year}_{month:02d}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    def _display_employee_comparison(self, year: int, month: int):
        """
        Display employee comparison report.
        
        Args:
            year: Year
            month: Month
        """
        logger.info(f"Displaying employee comparison: {year}-{month:02d}")
        
        # Get reports
        reports = self.report_service.get_all_employees_report(year, month)
        
        if not reports:
            st.error("No data available")
            return
        
        # Display header
        st.markdown("---")
        month_name = self.calculator.get_month_name(month)
        st.header(f"📊 Employee Comparison - {month_name} {year}")
        
        # Create comparison chart data
        employee_names = [r['user_name'] for r in reports]
        working_days = [r['actual_working_days'] for r in reports]
        salaries = [r['salary'] for r in reports]
        
        # Working days comparison
        st.subheader("📅 Working Days Comparison")
        chart_data = pd.DataFrame({
            'Employee': employee_names,
            'Working Days': working_days
        })
        st.bar_chart(chart_data.set_index('Employee'))
        
        # Salary comparison
        st.subheader("💰 Salary Comparison")
        chart_data = pd.DataFrame({
            'Employee': employee_names,
            'Salary (EGP)': salaries
        })
        st.bar_chart(chart_data.set_index('Employee'))
        
        # Statistics
        st.subheader("📊 Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_working_days = sum(working_days) / len(working_days)
            st.metric("Average Working Days", f"{avg_working_days:.1f}")
        
        with col2:
            avg_salary = sum(salaries) / len(salaries)
            st.metric("Average Salary", CurrencyHelper.format_currency(avg_salary))
        
        with col3:
            max_salary = max(salaries)
            st.metric("Highest Salary", CurrencyHelper.format_currency(max_salary))


def render_reports_page():
    """
    Main function to render reports page.
    
    Called from app.py when user navigates to reports.
    """
    reports = ReportsPage()
    reports.render()