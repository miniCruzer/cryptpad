import unittest

from cryptpad import encrypt, decrypt, mkpasswd, get_signature, MAC_SIZE, AuthenticationError

test_data = "<avenj> Goodnight, NSA."
test_pass = "P3rl!"

class TestEncryption(unittest.TestCase):

	def test_mkpasswd_encrytion_key(self):

		Ek, Ak = mkpasswd(test_pass)
		self.assertEqual('d\xf8L\xd4S\xf1@9\x83\xa6\xfd\x83\xa9\x9c\xad\x11\xba\xd0\xb6\xfc\x15\xf6s\r\xeb\xae\\~{~\x87\xcc', Ek)

	def test_mkpasswd_authentication_key(self):

		Ek, Ak = mkpasswd(test_pass)
		self.assertEqual('6^\x9b\xc5\xdb\xfd\x80\xe89g\xcec4V\x81\xc4\xff\xf3&\xc9\x92\x81\xc2\xe4<U\x10S\t\x12\x93\xf1', Ak)

	def test_decrypt_succeeds(self):

		Ek, Ak = mkpasswd(test_pass)

		encrypted_data = encrypt(test_data, Ek, Ak).getvalue()

		Ek, Ak = mkpasswd(test_pass)

		decrypted_data = decrypt(encrypted_data, Ek, Ak).getvalue()

		self.assertEqual(decrypted_data, test_data)

	def test_auth_fail_bad_mac(self):
		"""cuts off the real MAC and puts in some bogus HMAC-SHA256 signature 
		that will cause decrypt() to raise an Exception."""

		Ek, Ak = mkpasswd(test_data)

		encrypted_data = encrypt(test_data, Ek, Ak).getvalue()

		bad_mac = get_signature("bogus data", Ak)
		encrypted_data = encrypted_data[:-MAC_SIZE] + bad_mac

		with self.assertRaises(AuthenticationError):
			decrypt(encrypted_data, Ek, Ak)



if __name__ == '__main__':
	unittest.main()