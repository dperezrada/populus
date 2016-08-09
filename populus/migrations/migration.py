import itertools

from toposort import toposort

from .registrar import (
    get_compiled_registrar_contract,
    generate_registrar_value_setters,
    Bool,
)

from .validation import (
    validate_migration_classes,
)


class Migration(object):
    migration_id = None
    dependencies = None
    operations = None
    compiled_contracts = None

    registrar_address = None
    web3 = None

    def __init__(self, web3, registrar):
        self.web3 = web3
        self.registrar = registrar

    @property
    def migration_key(self):
        if self.migration_id is None:
            raise ValueError("Migrations must have a `migration_id`")
        key = "migration/{migration_id}".format(
            migration_id=self.migration_id,
        )
        return key

    @property
    def has_been_executed(self):
        if not self.registrar.call().exists(self.migration_key):
            return False
        return self.registrar.call().getBool(self.migration_key)

    def mark_as_executed(self):
        Bool(self.registrar, key=self.migration_key, value=True).set()

    def process_operation_receipt(self, operation_key, receipt):
        registrar_setters = generate_registrar_value_setters(
            receipt,
            prefix=operation_key,
        )
        for Setter in registrar_setters:
            Setter(self.registrar).set()

        # mark the operation as having been completed.
        Bool(self.registrar, key=operation_key, value=True).set()

    def execute(self):
        if self.registrar.call().exists(self.migration_key):
            raise ValueError("This migration has already been run")

        for operation_index, operation in enumerate(self.operations):
            operation_key = "{prefix}/operation/{operation_index}".format(
                prefix=self.migration_key,
                operation_index=operation_index,
            )

            operation_alread_executed = (
                self.registrar.call().exists(operation_key) and
                self.registrar.call().getBool(operation_key)
            )
            if operation_alread_executed:
                # raise or continue?
                raise ValueError("This operation has already been run")

            operation_receipt = operation.execute(
                web3=self.web3,
                compiled_contracts=self.compiled_contracts,
                registrar=self.registrar,
            )

            self.process_operation_receipt(operation_key, operation_receipt)


def sort_migrations(migration_classes):
    migration_dependency_graph = {
        m.migration_id: set() if m.dependencies is None else set(m.dependencies)
        for m in migration_classes
    }

    migration_classes_by_id = {
        m.migration_id: m for m in migration_classes
    }
    migration_id_order = toposort(migration_dependency_graph)
    migration_order = [
        {migration_classes_by_id[migration_id] for migration_id in execution_set}
        for execution_set in migration_id_order
    ]
    return migration_order


def run_migrations(migration_classes, web3, registrar_address):
    validate_migration_classes(migration_classes)

    sorted_migration_classes = sort_migrations(migration_classes)
    sorted_migrations = [
        migration_class(web3, registrar_address)
        for migration_class
        in itertools.chain.from_iterable(sorted_migration_classes)
    ]
    migrations_to_run = [
        migration_instance
        for migration_instance
        in sorted_migrations
        if not migration_instance.has_been_executed
    ]
    for migration_instance in migrations_to_run:
        migration_instance.execute()
