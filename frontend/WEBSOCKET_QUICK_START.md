# WebSocket Integration - Quick Start Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Start Backend (30 seconds)
```bash
cd rd_tax_agent
python main.py
```

Wait for:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 2: Test Connection (1 minute)
```bash
python test_websocket_connection.py
```

Expected output:
```
✓ Connection established successfully!
✓ Welcome message received
✓ Test message sent
✓ Echo response received
✓ All tests passed!
```

### Step 3: Open Test Page (1 minute)
Open in browser:
```
http://localhost:8000/frontend/test_websocket.html
```

Verify:
- ✅ Status shows "Connected ✓" (green)
- ✅ Connection ID displayed
- ✅ Message log shows connection confirmation

### Step 4: Open Workflow Page (1 minute)
Open in browser:
```
http://localhost:8000/frontend/workflow.html
```

Verify:
- ✅ Backend Status shows "Connected" (green badge)
- ✅ Log shows "Connected to backend successfully"
- ✅ All 6 stages visible with "Pending" status

### Step 5: Test Reconnection (1 minute)
1. Stop backend (Ctrl+C)
2. Observe "Disconnected" status in frontend
3. Restart backend
4. Observe automatic reconnection

---

## 📋 Quick Reference

### WebSocket URL
```
ws://localhost:8000/ws
```

### Message Types

**Status Update**:
```javascript
{
  type: "status_update",
  stage: "data_ingestion",
  status: "in_progress",
  details: "Processing..."
}
```

**Error**:
```javascript
{
  type: "error",
  error_type: "api_connection",
  message: "Connection failed"
}
```

**Progress**:
```javascript
{
  type: "progress",
  current_step: 15,
  total_steps: 50,
  percentage: 30.0
}
```

### Stage Mapping

| Backend | Frontend | Display Name |
|---------|----------|--------------|
| `data_ingestion` | Stage 1 | Data Ingestion |
| `qualification` | Stage 3 | Project Qualification |
| `audit_trail` | Stage 6 | PDF Generation |

### Status Values

| Status | Display | Color |
|--------|---------|-------|
| `pending` | Pending | Gray |
| `in_progress` | In Progress | Blue |
| `completed` | Completed | Green |
| `error` | Error | Red |

---

## 🔧 Troubleshooting

### Connection Failed
**Problem**: Cannot connect to WebSocket

**Solution**:
1. Check backend is running: `python main.py`
2. Verify URL: `ws://localhost:8000/ws`
3. Check firewall settings

### No Messages
**Problem**: Connected but no updates

**Solution**:
1. Check browser console for errors
2. Verify message handlers are set up
3. Check backend logs

### Frequent Disconnects
**Problem**: Connection drops often

**Solution**:
1. Check network stability
2. Verify backend is not crashing
3. Check backend logs for errors

---

## 📚 Documentation

- **Full Guide**: `WEBSOCKET_INTEGRATION.md`
- **Testing**: `VERIFICATION_STEPS.md`
- **Implementation**: `TASK_135_IMPLEMENTATION_SUMMARY.md`
- **Test Results**: `TASK_135_TEST_RESULTS.md`

---

## ✅ Success Criteria

You know it's working when:
- ✅ Backend status shows "Connected" (green)
- ✅ No errors in browser console
- ✅ No errors in backend logs
- ✅ Test script passes all tests
- ✅ Reconnection works automatically

---

## 🎯 Next Steps

1. ✅ Task 135 complete
2. 🔜 Task 136: Add "Run Pipeline" button
3. 🔜 Test real workflow execution

---

**Need Help?** Check the full documentation in `WEBSOCKET_INTEGRATION.md`
