"""SenWeaver command module - helper functions and utilities."""

from .helper import create_module, get_tables


def register_commands(app):
    """Register all CLI commands from modules."""
    from senweaver.command.core import create, createsuperuser, crud, data

    # Register each command module
    create.concole(app)
    crud.concole(app)
    data.concole(app)
    createsuperuser.concole(app)


__all__ = ['create_module', 'get_tables', 'register_commands']
