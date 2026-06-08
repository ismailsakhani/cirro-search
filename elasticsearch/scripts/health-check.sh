#!/usr/bin/env bash
set -euo pipefail

ES_URL="${ES_URL:-http://localhost:9200}"
KIBANA_URL="${KIBANA_URL:-http://localhost:5601}"

echo "Checking Elasticsearch at ${ES_URL}..."
ES_RESPONSE="$(curl -sf "${ES_URL}/_cluster/health?wait_for_status=yellow&timeout=10s")"
ES_STATUS="$(echo "${ES_RESPONSE}" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)"

if [[ "${ES_STATUS}" != "green" && "${ES_STATUS}" != "yellow" ]]; then
  echo "FAIL: Elasticsearch status is '${ES_STATUS}'"
  exit 1
fi

echo "OK: Elasticsearch status is ${ES_STATUS}"

echo "Checking Kibana at ${KIBANA_URL}..."
KIBANA_RESPONSE="$(curl -sf "${KIBANA_URL}/api/status")"

if ! echo "${KIBANA_RESPONSE}" | grep -q '"level":"available"'; then
  echo "FAIL: Kibana is not available"
  exit 1
fi

echo "OK: Kibana is available"
echo "Health check passed."
