from web3 import Web3
from eth_account import Account
from .config import GANACHE_RPC, PRIVATE_KEY, CONTRACT_ADDRESS


# -------------------------------------------------
# Smart Contract ABI
# (Paste ABI printed from deploy_contract() here)
# -------------------------------------------------
contract_abi = [
    {
        "inputs": [{"internalType": "string", "name": "", "type": "string"}],
        "name": "certificates",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "_hash", "type": "string"}],
        "name": "storeCertificate",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "_hash", "type": "string"}],
        "name": "verifyCertificate",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    }
]


# -------------------------------------------------
# Lazy connection helper
# -------------------------------------------------
_web3 = None
_contract = None
_account = None
_account_address = None


def get_web3():
    """Lazy initialization of Web3 connection."""
    global _web3
    if _web3 is None:
        _web3 = Web3(Web3.HTTPProvider(GANACHE_RPC))
    return _web3


def get_contract():
    """Lazy initialization of smart contract."""
    global _contract
    if _contract is None:
        web3 = get_web3()
        _contract = web3.eth.contract(
            address=CONTRACT_ADDRESS,
            abi=contract_abi
        )
    return _contract


def get_account():
    """Lazy initialization of account."""
    global _account, _account_address
    if _account is None:
        _account = Account.from_key(PRIVATE_KEY)
        _account_address = _account.address
    return _account, _account_address


def is_blockchain_connected():
    """Check if blockchain is connected."""
    web3 = get_web3()
    return web3.is_connected()


# -------------------------------------------------
# Store Certificate Hash on Blockchain
# -------------------------------------------------
def store_hash_on_blockchain(hash_value):

    web3 = get_web3()
    contract = get_contract()
    account, account_address = get_account()

    # Prevent duplicate storage
    if verify_hash_from_blockchain(hash_value):
        raise Exception("Certificate already exists on blockchain")

    nonce = web3.eth.get_transaction_count(account_address)

    transaction = contract.functions.storeCertificate(hash_value).build_transaction({
        "from": account_address,
        "nonce": nonce,
        "gas": 2000000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = account.sign_transaction(transaction)

    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

    return receipt.transactionHash.hex()


# -------------------------------------------------
# Verify Certificate Hash from Blockchain
# -------------------------------------------------
def verify_hash_from_blockchain(hash_value):

    contract = get_contract()
    return contract.functions.verifyCertificate(hash_value).call()
