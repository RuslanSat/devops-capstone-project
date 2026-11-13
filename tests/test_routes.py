"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_get_account(self):
        """It should Read a persisted account by id"""
        account = self._create_accounts(1)[0]
        response = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), account.serialize())

    def test_get_account_not_found(self):
        """It should return JSON 404 for an unknown account"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.get_json()["error"], "Not Found")

    def test_list_accounts(self):
        """It should List every persisted account exactly once"""
        accounts = self._create_accounts(3)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item["id"] for item in response.get_json()},
            {account.id for account in accounts},
        )
        self.assertEqual(len(response.get_json()), 3)

    def test_list_empty_accounts(self):
        """It should return an empty JSON list for an empty collection"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), [])

    def test_update_account(self):
        """It should Update all fields and persist them for a later read"""
        account = self._create_accounts(1)[0]
        changed = AccountFactory().serialize()
        changed["id"] = account.id
        response = self.client.put(f"{BASE_URL}/{account.id}", json=changed)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json(), changed)
        read_back = self.client.get(f"{BASE_URL}/{account.id}")
        self.assertEqual(read_back.get_json(), changed)

    def test_update_cannot_change_account_id(self):
        """It should retain the URL identity when a payload supplies another id"""
        account = self._create_accounts(1)[0]
        changed = account.serialize()
        changed["id"] = account.id + 1234
        response = self.client.put(f"{BASE_URL}/{account.id}", json=changed)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["id"], account.id)
        self.assertEqual(Account.all()[0].id, account.id)

    def test_update_not_found(self):
        """It should not create a resource while updating an unknown id"""
        response = self.client.put(f"{BASE_URL}/0", json=AccountFactory().serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Account.all(), [])

    def test_update_invalid_account(self):
        """It should reject an incomplete replacement without saving it"""
        account = self._create_accounts(1)[0]
        original = account.serialize()
        response = self.client.put(f"{BASE_URL}/{account.id}", json={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Account.find(account.id).serialize(), original)

    def test_update_unsupported_media_type(self):
        """It should reject updates with a non-JSON request body"""
        account = self._create_accounts(1)[0]
        response = self.client.put(
            f"{BASE_URL}/{account.id}", data="invalid", content_type="text/plain"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_account(self):
        """It should Delete an account and return an empty 204 response"""
        account = self._create_accounts(1)[0]
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")
        self.assertIsNone(Account.find(account.id))
        self.assertEqual(
            self.client.get(f"{BASE_URL}/{account.id}").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_delete_unknown_account_is_idempotent(self):
        """It should return 204 when an account was already deleted"""
        account = self._create_accounts(1)[0]
        self.client.delete(f"{BASE_URL}/{account.id}")
        response = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data, b"")

    def test_create_location_resolves_to_created_account(self):
        """It should expose a usable Location for the newly created resource"""
        response = self.client.post(BASE_URL, json=AccountFactory().serialize())
        location = response.headers["Location"]
        self.assertTrue(location.endswith(f"{BASE_URL}/{response.get_json()['id']}"))
        found = self.client.get(location)
        self.assertEqual(found.status_code, status.HTTP_200_OK)
        self.assertEqual(found.get_json(), response.get_json())

    def test_security_headers(self):
        """It should protect API responses without redirecting lab HTTP traffic"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("default-src", response.headers["Content-Security-Policy"])

    def test_cors(self):
        """It should allow an approved browser origin to read the public API"""
        response = self.client.get(
            BASE_URL, headers={"Origin": "https://client.example.com"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            "https://client.example.com",
        )

    def test_unsupported_method(self):
        """It should reject methods outside the REST contract with JSON 405"""
        response = self.client.patch(BASE_URL, json={})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.get_json()["error"], "Method not Allowed")

