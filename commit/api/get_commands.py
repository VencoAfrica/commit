import importlib
import sys
import traceback
import os
import frappe
from frappe.utils.bench_helper import get_app_commands

@frappe.whitelist()
def get_project_app_commands(app: str, app_path: str = None) -> dict:
    '''
        Gets the commands for the app
    '''
    # Validate app against installed apps only — never trust client-supplied paths
    installed_apps = frappe.get_installed_apps()
    if app not in installed_apps:
        frappe.throw("App not found", frappe.DoesNotExistError)
    app_path = None  # Never trust client-supplied paths

    # Check the permissions of the user
    if not is_system_manager():
        return frappe.throw('You do not have permission to access this resource', frappe.PermissionError)
    return get_site_app_commands(app)

@frappe.whitelist()
def get_site_app_commands(app: str) -> dict:
    try:
        app_command_module = importlib.import_module(f"{app}.commands")
     # Call get_commands if it is a callable
    except ModuleNotFoundError as e:
        if e.name == f"{app}.commands":
            return []
        traceback.print_exc()
        return []

    command_list = []
    if hasattr(app_command_module, 'commands'):
        commands_from_function = app_command_module.commands
        if commands_from_function:
            for command_instance in commands_from_function:
                help_text = getattr(command_instance, 'help', 'No help text available')
                name = getattr(command_instance, 'name', [])
                obj = {
                    'name': name,
                    'help': help_text
                }
                command_list.append(obj)
    return command_list

def is_system_manager():
    user = frappe.session.user
    roles = frappe.get_roles(user)
    return 'System Manager' in roles
