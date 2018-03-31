from hashlib import blake2b, sha256


def blake_hash(payload, size=16):
    h = blake2b(digest_size=size)
    h.update(payload)

    return h.hexdigest()


def sha256_hash(payload):
    h = sha256()
    h.update(payload)

    return h.hexdigest()
