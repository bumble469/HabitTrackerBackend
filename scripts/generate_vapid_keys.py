import base64
from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid

v = Vapid()
v.generate_keys()
b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
private = b64(v.private_key.private_numbers().private_value.to_bytes(32, "big"))
public = b64(v.public_key.public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))
print("VAPID_PRIVATE_KEY=" + private)
print("VAPID_PUBLIC_KEY=" + public)