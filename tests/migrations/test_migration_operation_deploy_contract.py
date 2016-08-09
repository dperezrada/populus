import pytest

from populus.migrations import (
    DeployContract,
    Address,
)
from populus.utils.transactions import (
    wait_for_transaction_receipt,
    get_contract_address_from_txn,
)
from populus.utils.contracts import (
    link_contract,
)


def test_deploy_contract_operation_on_math_contract(web3, MATH):
    deploy_contract_operation = DeployContract('Math', timeout=30)

    operation_receipt = deploy_contract_operation.execute(
        web3=web3,
        compiled_contracts={'Math': MATH},
    )
    deploy_txn_hash = operation_receipt['deploy-transaction-hash']
    contract_address = get_contract_address_from_txn(web3, deploy_txn_hash, timeout=30)

    code = web3.eth.getCode(contract_address)

    assert code == MATH['code_runtime']


def test_deploy_contract_operation_with_arguments(web3, WITH_CONSTRUCTOR_ARGUMENTS):
    deploy_contract_operation = DeployContract(
        'WithConstructorArguments',
        timeout=30,
        arguments=[12345, 'a-string-argument-thats-32-bytes'],
    )

    operation_receipt = deploy_contract_operation.execute(
        web3=web3,
        compiled_contracts={'WithConstructorArguments': WITH_CONSTRUCTOR_ARGUMENTS},
    )
    deploy_txn_hash = operation_receipt['deploy-transaction-hash']
    contract_address = get_contract_address_from_txn(web3, deploy_txn_hash, timeout=30)

    code = web3.eth.getCode(contract_address)

    assert code == WITH_CONSTRUCTOR_ARGUMENTS['code_runtime']

    ContractFactory = web3.eth.contract(**WITH_CONSTRUCTOR_ARGUMENTS)
    contract = ContractFactory(address=contract_address)

    assert contract.call().data_a() == 12345
    assert contract.call().data_b() == 'a-string-argument-thats-32-bytes'


def test_deploy_contract_failure_during_deployment(web3, THROWER):
    deploy_contract_operation = DeployContract(
        'Thrower',
        timeout=30,
        arguments=[True],
    )

    with pytest.raises(ValueError):
        deploy_contract_operation.execute(
            web3=web3,
            compiled_contracts={'Thrower': THROWER},
        )
