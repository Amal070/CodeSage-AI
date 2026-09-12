// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificateStorage {

    struct Certificate {
        string hashValue;
        address issuedBy;
        uint256 timestamp;
    }

    mapping(string => Certificate) private certificates;

    function storeCertificate(string memory _hash) public {

        require(bytes(certificates[_hash].hashValue).length == 0,
                "Certificate already exists");

        certificates[_hash] = Certificate({
            hashValue: _hash,
            issuedBy: msg.sender,
            timestamp: block.timestamp
        });
    }

    function verifyCertificate(string memory _hash)
        public
        view
        returns (bool)
    {
        return bytes(certificates[_hash].hashValue).length > 0;
    }

    function getCertificate(string memory _hash)
        public
        view
        returns (string memory, address, uint256)
    {
        Certificate memory cert = certificates[_hash];
        return (cert.hashValue, cert.issuedBy, cert.timestamp);
    }
}