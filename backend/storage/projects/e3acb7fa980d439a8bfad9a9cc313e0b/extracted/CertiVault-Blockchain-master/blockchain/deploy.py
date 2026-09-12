from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version
from eth_account import Account
from .config import GANACHE_RPC, PRIVATE_KEY


# -----------------------------
# Smart Contract Code
# -----------------------------
contract_source = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

contract CertificateStorage {

    mapping(string => bool) public certificates;

    function storeCertificate(string memory _hash) public {
        require(!certificates[_hash], "Certificate already exists");
        certificates[_hash] = true;
    }

    function verifyCertificate(string memory _hash)
        public
        view
        returns (bool)
    {
        return certificates[_hash];
    }
}
"""


# -----------------------------
# Deploy Function
# -----------------------------
def deploy_contract():

    print("Installing Solidity Compiler...")
    install_solc("0.8.17")
    set_solc_version("0.8.17")

    print("Compiling Contract...")
    compiled = compile_source(contract_source, output_values=["abi", "bin"])
    contract_id, contract_interface = compiled.popitem()

    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]

    print("Connecting to Ganache...")
    w3 = Web3(Web3.HTTPProvider(GANACHE_RPC))

    if not w3.is_connected():
        raise Exception("❌ Cannot connect to Ganache")

    account = Account.from_key(PRIVATE_KEY)
    account_address = account.address

    print("Using Account:", account_address)

    nonce = w3.eth.get_transaction_count(account_address)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)

    print("Deploying Contract...")

    transaction = Contract.constructor().build_transaction({
        "from": account_address,
        "nonce": nonce,
        "gas": 2000000,
        "gasPrice": w3.eth.gas_price,
    })

    signed_tx = account.sign_transaction(transaction)

    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("Waiting for transaction receipt...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    print("✅ Contract Deployed Successfully!")

    return receipt.contractAddress, abi