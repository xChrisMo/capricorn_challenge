#!/bin/bash
echo "======================================"
echo "Running All Plugin Tests"
echo "======================================"
echo ""

failed=0

echo "1. Testing MCP Server Protocol..."
python mcp/test_server.py
if [ $? -ne 0 ]; then failed=$((failed + 1)); fi
echo ""

echo "2. Testing Git Integration..."
python mcp/test_git_integration.py
if [ $? -ne 0 ]; then failed=$((failed + 1)); fi
echo ""

echo "3. Testing Categorization & Risk Scoring..."
python mcp/test_categorization.py
if [ $? -ne 0 ]; then failed=$((failed + 1)); fi
echo ""

echo "4. Testing Aggregation..."
python mcp/test_aggregator.py
if [ $? -ne 0 ]; then failed=$((failed + 1)); fi
echo ""

echo "5. Testing File I/O..."
python mcp/test_file_utils.py
if [ $? -ne 0 ]; then failed=$((failed + 1)); fi
echo ""

echo "======================================"
if [ $failed -eq 0 ]; then
    echo "✅ ALL TESTS PASSED!"
else
    echo "❌ $failed test suite(s) failed"
fi
echo "======================================"
exit $failed
