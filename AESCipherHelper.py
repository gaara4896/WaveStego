from Crypto.Cipher import AES

from HashHelper import blake_hash


def encrypt(payload, passphrase):
    (key, iv) = get_key(passphrase)

    obj = AES.new(key, AES.MODE_CBC, iv)

    while len(payload) % 16 != 0:
        payload += " "

    return obj.encrypt(payload)


def decrypt(encrypted_payload, passphrase):
    (key, iv) = get_key(passphrase)

    obj = AES.new(key, AES.MODE_CBC, iv)

    return obj.decrypt(encrypted_payload).strip()


def get_key(passphrase):
    key = blake_hash(passphrase.encode())
    iv = blake_hash(passphrase.encode(), size=8)

    return (key, iv)
