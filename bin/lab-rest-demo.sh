#!/usr/bin/env bash
# Run against this project's local course-lab service, never a production account DB.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p evidence
BASE_URL="${ACCOUNTS_DEMO_URL:-http://127.0.0.1:5000}"
CREATE_DATA='{"name":"John Doe","email":"john@doe.com","address":"123 Main St.","phone_number":"555-1212"}'
UPDATE_DATA='{"name":"John Doe","email":"john@doe.com","address":"123 Main St.","phone_number":"555-1111"}'

{
  echo "curl -i -X POST $BASE_URL/accounts -H 'Content-Type: application/json' -d '$CREATE_DATA'"
  curl -fsS -i -X POST "$BASE_URL/accounts" -H 'Content-Type: application/json' -d "$CREATE_DATA"
  echo
} | tee evidence/rest-create-done.txt
ACCOUNT_ID=$(python - <<'PY'
import json
from pathlib import Path
content = Path('evidence/rest-create-done.txt').read_text()
data = json.loads(content[content.index('{', content.index('HTTP/')):])
print(data['id'])
PY
)

{
  echo "curl -i -X GET $BASE_URL/accounts"
  curl -fsS -i "$BASE_URL/accounts"
  echo
} | tee evidence/rest-list-done.txt
{
  echo "curl -i -X GET $BASE_URL/accounts/$ACCOUNT_ID"
  curl -fsS -i "$BASE_URL/accounts/$ACCOUNT_ID"
  echo
} | tee evidence/rest-read-done.txt
{
  echo "curl -i -X PUT $BASE_URL/accounts/$ACCOUNT_ID -H 'Content-Type: application/json' -d '$UPDATE_DATA'"
  curl -fsS -i -X PUT "$BASE_URL/accounts/$ACCOUNT_ID" -H 'Content-Type: application/json' -d "$UPDATE_DATA"
  echo
} | tee evidence/rest-update-done.txt
{
  echo "curl -i -X DELETE $BASE_URL/accounts/$ACCOUNT_ID"
  curl -fsS -i -X DELETE "$BASE_URL/accounts/$ACCOUNT_ID"
  echo
} | tee evidence/rest-delete-done.txt
python - <<'PY'
from pathlib import Path
import json
for action in ['create', 'list', 'read', 'update', 'delete']:
    content = Path(f'evidence/rest-{action}-done.txt').read_text()
    expected = {'create': '201', 'delete': '204'}.get(action, '200')
    assert f' {expected} ' in content, f'{action}: wrong HTTP status'
    if action == 'update':
        data = json.loads(content[content.index('{', content.index('HTTP/')):])
        assert data['phone_number'] == '555-1111'
print('All five actual curl requests returned the expected HTTP statuses.')
PY
