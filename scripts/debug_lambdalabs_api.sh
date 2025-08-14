#!/bin/bash

echo "Lambda Labs API Diagnostic Script"
echo "================================="
echo

# Get API key from credentials file
API_KEY=$(python3 $(dirname "$0")/lambdalabs_credentials.py get 2>/dev/null)
if [ -z "$API_KEY" ]; then
    echo "❌ Lambda Labs API key not found"
    echo "   Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'"
    exit 1
else
    echo "✓ Lambda Labs API key loaded from credentials"
    echo "  Key starts with: ${API_KEY:0:10}..."
    echo "  Key length: ${#API_KEY} characters"
fi

echo
echo "Testing API Access:"
echo "-------------------"

# Test with curl to get more detailed error information
echo "1. Testing instance types endpoint..."
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" \
    https://cloud.lambdalabs.com/api/v1/instance-types 2>&1)
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "   ✓ API access successful"
    echo "   Instance types available: $(echo "$body" | grep -o '"name"' | wc -l)"
elif [ "$http_code" = "403" ]; then
    echo "   ❌ Access forbidden (HTTP 403)"
    echo "   Error: $body"
    echo
    echo "   Possible causes:"
    echo "   - Invalid or expired API key"
    echo "   - API key doesn't have necessary permissions"
    echo "   - IP address or region restrictions"
    echo "   - Rate limiting"
    echo
    echo "   Please verify:"
    echo "   1. Your API key is correct and active"
    echo "   2. You're not behind a VPN that might be blocked"
    echo "   3. Your Lambda Labs account is in good standing"
elif [ "$http_code" = "401" ]; then
    echo "   ❌ Unauthorized (HTTP 401)"
    echo "   Your API key appears to be invalid or malformed"
else
    echo "   ❌ Unexpected response (HTTP $http_code)"
    echo "   Response: $body"
fi

echo
echo "2. Testing SSH keys endpoint..."
response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $API_KEY" \
    https://cloud.lambdalabs.com/api/v1/ssh-keys 2>&1)
http_code=$(echo "$response" | tail -n 1)
body=$(echo "$response" | head -n -1)

if [ "$http_code" = "200" ]; then
    echo "   ✓ Can access SSH keys"
    # Try to find the kdevops key
    if echo "$body" | grep -q "kdevops-lambdalabs"; then
        echo "   ✓ Found 'kdevops-lambdalabs' SSH key"
    else
        echo "   ⚠ 'kdevops-lambdalabs' SSH key not found"
        echo "   Available keys:"
        echo "$body" | grep -o '"name":"[^"]*"' | sed 's/"name":"/ - /g' | sed 's/"//g'
    fi
else
    echo "   ❌ Cannot access SSH keys (HTTP $http_code)"
fi

echo
echo "Troubleshooting Steps:"
echo "----------------------"
echo "1. Verify your API key at: https://cloud.lambdalabs.com/api-keys"
echo "2. Create a new API key if needed"
echo "3. Ensure you're not using a VPN that might be blocked"
echo "4. Try accessing the API from a different network/location"
echo "5. Contact Lambda Labs support if the issue persists"
echo
echo "For manual testing, try:"
echo "API_KEY=\$(python3 scripts/lambdalabs_credentials.py get)"
echo "curl -H \"Authorization: Bearer \$API_KEY\" https://cloud.lambdalabs.com/api/v1/instance-types"
