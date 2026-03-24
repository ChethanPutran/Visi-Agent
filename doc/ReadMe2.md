Excellent! You have a solid foundation with your Visi-Agent system. Let me help you evolve it from a batch RAG system to a **Real-Time Streaming Analytics Platform**. This transformation will enable live video monitoring, real-time alerts, and continuous analytics.

## Architecture Transformation: Batch → Streaming

### Current Architecture (Batch RAG)
```
Video Upload → Process → Index → Query
     ↓           ↓        ↓        ↓
  (File)     (Single)  (Static)  (Manual)
```

### Target Architecture (Streaming Analytics)
```
Live Stream → Real-time Processing → Event Stream → Analytics → Alerts
     ↓              ↓                    ↓           ↓         ↓
  (RTMP/WebRTC) (Pipeline)           (Kafka)    (Flink)   (WebSocket)
```

---

## 1. Enhanced Folder Structure for Streaming

```python
video-analytics-system/
├── src/
│   ├── streaming/                    # NEW: Streaming components
│   │   ├── __init__.py
│   │   ├── ingesters/                # Stream ingestion
│   │   │   ├── __init__.py
│   │   │   ├── rtmp_ingester.py      # RTMP stream ingestion
│   │   │   ├── webrtc_ingester.py    # WebRTC for browser streams
│   │   │   ├── camera_ingester.py    # IP camera ingestion
│   │   │   └── file_watcher.py       # Watch for new video files
│   │   ├── processors/               # Stream processors
│   │   │   ├── __init__.py
│   │   │   ├── frame_processor.py    # Frame-by-frame processing
│   │   │   ├── window_processor.py   # Time-window aggregation
│   │   │   └── state_manager.py      # Stateful stream processing
│   │   ├── analytics/                # Real-time analytics
│   │   │   ├── __init__.py
│   │   │   ├── event_detector.py     # Real-time event detection
│   │   │   ├── anomaly_scorer.py     # Anomaly scoring
│   │   │   ├── aggregator.py         # Real-time aggregations
│   │   │   └── pattern_matcher.py    # Pattern matching
│   │   ├── alerts/                   # Alerting system
│   │   │   ├── __init__.py
│   │   │   ├── alert_engine.py       # Alert rules engine
│   │   │   ├── notifiers.py          # WebSocket/Email/SMS
│   │   │   └── alert_store.py        # Alert persistence
│   │   └── dashboards/               # Real-time dashboards
│   │       ├── __init__.py
│   │       ├── websocket_manager.py  # WebSocket connections
│   │       ├── metrics_streamer.py   # Real-time metrics
│   │       └── visualizations.py     # Live charts/graphs
│   │
│   ├── processing/
│   │   ├── streaming_models/         # NEW: Lightweight models for streaming
│   │   │   ├── __init__.py
│   │   │   ├── mobile_vision.py      # MobileNet/YOLO for real-time
│   │   │   ├── fast_transcriber.py   # Streaming ASR (whisper-tiny)
│   │   │   └── quantization.py       # Model quantization
│   │   └── batch/                    # Move existing processing here
│   │       └── ...                   # Your existing processing modules
│   │
│   └── messaging/                    # NEW: Message bus integration
│       ├── __init__.py
│       ├── kafka_producer.py         # Kafka event producer
│       ├── kafka_consumer.py         # Kafka event consumer
│       ├── event_schemas.py          # Avro/JSON schemas
│       └── stream_topics.py          # Topic definitions
```

---

## 2. Core Streaming Components Implementation

### A. Stream Ingester with Kafka

```python
# src/streaming/ingesters/rtmp_ingester.py
import asyncio
import cv2
import numpy as np
from aiokafka import AIOKafkaProducer
import json
from typing import AsyncGenerator
import logging

class RTMPIngester:
    """Ingest RTMP streams and publish frames to Kafka"""
    
    def __init__(self, stream_url: str, topic: str, bootstrap_servers: list):
        self.stream_url = stream_url
        self.topic = topic
        self.producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode()
        )
        self.cap = None
        self.running = False
        
    async def start(self):
        """Start the ingester"""
        await self.producer.start()
        self.running = True
        self.cap = cv2.VideoCapture(self.stream_url)
        
        # Set buffer size to reduce latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logging.warning(f"Failed to read frame from {self.stream_url}")
                await asyncio.sleep(0.1)
                continue
                
            # Convert frame to base64 for transport
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_b64 = base64.b64encode(buffer).decode()
            
            # Publish to Kafka
            await self.producer.send(
                self.topic,
                value={
                    'stream_id': self.stream_url,
                    'timestamp': time.time(),
                    'frame': frame_b64,
                    'frame_number': self.frame_count
                }
            )
            self.frame_count += 1
            
            # Control FPS - don't process faster than source
            await asyncio.sleep(1/30)  # Assuming 30fps
            
    async def stop(self):
        """Stop the ingester"""
        self.running = False
        if self.cap:
            self.cap.release()
        await self.producer.stop()
```

### B. Stream Processor with Windowed Aggregations

```python
# src/streaming/processors/window_processor.py
from flink import StreamExecutionEnvironment, TimeCharacteristic
from flink.table import StreamTableEnvironment
import pandas as pd
from typing import List, Dict

class WindowedVideoProcessor:
    """
    Process video streams with time windows using Apache Flink
    """
    
    def __init__(self, bootstrap_servers: str, group_id: str):
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_stream_time_characteristic(TimeCharacteristic.EventTime)
        self.table_env = StreamTableEnvironment.create(self.env)
        
        # Configure Kafka source
        self.table_env.execute_sql(f"""
            CREATE TABLE video_stream (
                stream_id STRING,
                timestamp TIMESTAMP(3),
                frame_bytes STRING,
                frame_number BIGINT,
                WATERMARK FOR timestamp AS timestamp - INTERVAL '5' SECOND
            ) WITH (
                'connector' = 'kafka',
                'topic' = 'video-frames',
                'properties.bootstrap.servers' = '{bootstrap_servers}',
                'properties.group.id' = '{group_id}',
                'format' = 'json',
                'scan.startup.mode' = 'latest-offset'
            )
        """)
        
    def define_windows(self):
        """Define various windowing strategies"""
        
        # Tumbling window: every 10 seconds
        tumbling_window_sql = """
            SELECT 
                stream_id,
                TUMBLE_START(timestamp, INTERVAL '10' SECOND) as window_start,
                COUNT(*) as frame_count,
                AVG(CAST(frame_number AS DOUBLE)) as avg_frame_num
            FROM video_stream
            GROUP BY 
                stream_id,
                TUMBLE(timestamp, INTERVAL '10' SECOND)
        """
        
        # Sliding window: 30-second window sliding every 5 seconds
        sliding_window_sql = """
            SELECT 
                stream_id,
                HOP_START(timestamp, INTERVAL '5' SECOND, INTERVAL '30' SECOND) as window_start,
                COUNT(*) as frame_count,
                COUNT(DISTINCT frame_bytes) as unique_frames
            FROM video_stream
            GROUP BY 
                stream_id,
                HOP(timestamp, INTERVAL '5' SECOND, INTERVAL '30' SECOND)
        """
        
        # Session window: gap of 10 seconds
        session_window_sql = """
            SELECT 
                stream_id,
                SESSION_START(timestamp, INTERVAL '10' SECOND) as session_start,
                COUNT(*) as events_in_session
            FROM video_stream
            GROUP BY 
                stream_id,
                SESSION(timestamp, INTERVAL '10' SECOND)
        """
        
        return {
            'tumbling': tumbling_window_sql,
            'sliding': sliding_window_sql,
            'session': session_window_sql
        }
    
    def add_stateful_processing(self):
        """Stateful processing with custom aggregations"""
        
        # Example: Track object counts per stream
        self.table_env.create_temporary_function(
            "track_objects", 
            ObjectTrackingUDAF()
        )
        
        stateful_query = """
            SELECT 
                stream_id,
                timestamp,
                track_objects(frame_bytes) as detected_objects,
                COUNT(*) OVER (
                    PARTITION BY stream_id 
                    ORDER BY timestamp 
                    ROWS BETWEEN 10 PRECEDING AND CURRENT ROW
                ) as rolling_frame_count
            FROM video_stream
        """
        
        return stateful_query


class ObjectTrackingUDAF:
    """Custom UDAF for tracking objects across frames"""
    
    def __init__(self):
        self.object_tracker = {}
        
    def accumulate(self, frame_bytes):
        # Decode frame
        frame = cv2.imdecode(
            np.frombuffer(base64.b64decode(frame_bytes), np.uint8), 
            cv2.IMREAD_COLOR
        )
        
        # Run lightweight object detection
        objects = self.detect_objects(frame)
        
        # Update tracking
        for obj in objects:
            obj_id = obj['id']
            if obj_id not in self.object_tracker:
                self.object_tracker[obj_id] = {
                    'first_seen': time.time(),
                    'last_seen': time.time(),
                    'count': 0
                }
            self.object_tracker[obj_id]['count'] += 1
            self.object_tracker[obj_id]['last_seen'] = time.time()
            
        return self.object_tracker
    
    def get_result(self):
        # Return objects that have been seen in the last 5 seconds
        current_time = time.time()
        active_objects = {
            obj_id: data 
            for obj_id, data in self.object_tracker.items()
            if current_time - data['last_seen'] < 5
        }
        return active_objects
```

### C. Real-Time Event Detection

```python
# src/streaming/analytics/event_detector.py
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class VideoEvent:
    """Event detected in video stream"""
    stream_id: str
    event_type: str
    timestamp: float
    confidence: float
    metadata: Dict[str, Any]
    frame_snapshot: str  # base64 encoded frame

class RealTimeEventDetector:
    """
    Detect events in real-time video streams
    """
    
    def __init__(self, model_path: str, alert_callback=None):
        self.model = self.load_model(model_path)
        self.alert_callback = alert_callback
        self.event_history = []
        
    def load_model(self, path: str):
        """Load lightweight model for real-time inference"""
        # Example: YOLOv8 for real-time detection
        from ultralytics import YOLO
        model = YOLO(path)
        return model
    
    async def detect_motion(self, prev_frame, curr_frame, threshold=30):
        """Detect motion using frame differencing"""
        # Convert to grayscale
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate difference
        diff = cv2.absdiff(prev_gray, curr_gray)
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        
        # Calculate motion percentage
        motion_pct = np.sum(thresh > 0) / thresh.size
        
        if motion_pct > 0.05:  # 5% of frame changed
            return VideoEvent(
                stream_id="unknown",  # Will be filled by caller
                event_type="motion_detected",
                timestamp=time.time(),
                confidence=min(motion_pct * 2, 1.0),
                metadata={"motion_percentage": motion_pct},
                frame_snapshot=self.encode_frame(curr_frame)
            )
        return None
    
    async def detect_objects(self, frame, stream_id: str):
        """Detect specific objects of interest"""
        results = self.model(frame, conf=0.5)
        
        events = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                confidence = float(box.conf[0])
                
                # Define which objects are "events"
                event_types = {
                    'person': 'person_detected',
                    'car': 'vehicle_detected',
                    'fire': 'fire_detected',
                    'smoke': 'smoke_detected'
                }
                
                if class_name in event_types:
                    events.append(VideoEvent(
                        stream_id=stream_id,
                        event_type=event_types[class_name],
                        timestamp=time.time(),
                        confidence=confidence,
                        metadata={
                            'class': class_name,
                            'bbox': box.xyxy[0].tolist(),
                            'class_id': class_id
                        },
                        frame_snapshot=self.encode_frame(frame)
                    ))
        
        return events
    
    async def detect_anomaly(self, frame, stream_id: str):
        """Detect anomalous behavior using autoencoder"""
        # This would use a trained autoencoder for anomaly detection
        # Simplified example
        features = self.extract_features(frame)
        
        # Calculate reconstruction error
        reconstructed = self.autoencoder.predict(features)
        error = np.mean((features - reconstructed) ** 2)
        
        if error > self.anomaly_threshold:
            return VideoEvent(
                stream_id=stream_id,
                event_type="anomaly_detected",
                timestamp=time.time(),
                confidence=min(error / self.anomaly_threshold, 1.0),
                metadata={"reconstruction_error": error},
                frame_snapshot=self.encode_frame(frame)
            )
        return None
    
    def encode_frame(self, frame):
        """Encode frame to base64"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return base64.b64encode(buffer).decode()
    
    async def process_stream_batch(self, frames: List[np.ndarray], stream_id: str):
        """Process a batch of frames and return detected events"""
        events = []
        
        # Motion detection (needs consecutive frames)
        for i in range(1, len(frames)):
            motion_event = await self.detect_motion(frames[i-1], frames[i])
            if motion_event:
                motion_event.stream_id = stream_id
                events.append(motion_event)
        
        # Object detection on key frames (every 5th frame to save compute)
        for i, frame in enumerate(frames):
            if i % 5 == 0:  # Process every 5th frame
                obj_events = await self.detect_objects(frame, stream_id)
                events.extend(obj_events)
                
                # Anomaly detection on key frames
                anomaly_event = await self.detect_anomaly(frame, stream_id)
                if anomaly_event:
                    events.append(anomaly_event)
        
        return events
```

### D. Real-Time Alerting System

```python
# src/streaming/alerts/alert_engine.py
from typing import Dict, List, Any, Callable
import asyncio
from datetime import datetime, timedelta
import json
from enum import Enum

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertRule:
    """Define alert rules with conditions"""
    
    def __init__(self, name: str, condition: Callable, severity: AlertSeverity, 
                 cooldown: int = 60):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.cooldown = cooldown  # seconds
        self.last_triggered = None
        
    def should_trigger(self, event: Dict) -> bool:
        if self.last_triggered:
            if (datetime.now() - self.last_triggered).seconds < self.cooldown:
                return False
        return self.condition(event)

class AlertEngine:
    """
    Rule-based alerting engine for video analytics
    """
    
    def __init__(self, notifiers: List['Notifier']):
        self.rules = []
        self.notifiers = notifiers
        self.alert_history = []
        
    def add_rule(self, rule: AlertRule):
        """Add an alert rule"""
        self.rules.append(rule)
        
    async def process_event(self, event: VideoEvent):
        """Process an event and trigger alerts if rules match"""
        event_dict = {
            'stream_id': event.stream_id,
            'event_type': event.event_type,
            'timestamp': event.timestamp,
            'confidence': event.confidence,
            'metadata': event.metadata,
            'frame_snapshot': event.frame_snapshot
        }
        
        triggered_alerts = []
        for rule in self.rules:
            if rule.should_trigger(event_dict):
                alert = {
                    'rule_name': rule.name,
                    'severity': rule.severity.value,
                    'event': event_dict,
                    'triggered_at': datetime.now().isoformat()
                }
                triggered_alerts.append(alert)
                rule.last_triggered = datetime.now()
                
                # Send to notifiers
                for notifier in self.notifiers:
                    await notifier.send(alert)
                    
                # Store in history
                self.alert_history.append(alert)
                
        return triggered_alerts

# Example alert rules
def create_alert_rules():
    """Factory function to create common alert rules"""
    
    rules = []
    
    # Rule 1: Person in restricted area
    def restricted_area_condition(event):
        if event['event_type'] != 'person_detected':
            return False
        bbox = event['metadata'].get('bbox', [])
        # Check if bbox is in restricted zone (simplified)
        return bbox and bbox[0] > 100 and bbox[0] < 200
        
    rules.append(AlertRule(
        name="Person in restricted area",
        condition=restricted_area_condition,
        severity=AlertSeverity.CRITICAL,
        cooldown=30
    ))
    
    # Rule 2: High motion for > 10 seconds
    motion_count = {}
    def high_motion_condition(event):
        if event['event_type'] != 'motion_detected':
            return False
        
        stream_id = event['stream_id']
        current_time = event['timestamp']
        
        # Clean old events
        motion_count[stream_id] = [
            t for t in motion_count.get(stream_id, [])
            if current_time - t < 10
        ]
        
        motion_count[stream_id].append(current_time)
        
        # Alert if more than 10 motion events in 10 seconds
        return len(motion_count[stream_id]) > 10
        
    rules.append(AlertRule(
        name="Persistent motion detected",
        condition=high_motion_condition,
        severity=AlertSeverity.WARNING,
        cooldown=60
    ))
    
    # Rule 3: Fire/smoke detected
    def fire_condition(event):
        return event['event_type'] in ['fire_detected', 'smoke_detected']
        
    rules.append(AlertRule(
        name="Fire or smoke detected",
        condition=fire_condition,
        severity=AlertSeverity.EMERGENCY,
        cooldown=10
    ))
    
    return rules

# src/streaming/alerts/notifiers.py
import aiohttp
import asyncio
from typing import Dict, Any
import websockets

class WebSocketNotifier:
    """Send alerts to WebSocket clients"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        
    async def send(self, alert: Dict[str, Any]):
        """Send alert to all connected WebSocket clients"""
        await self.websocket_manager.broadcast({
            'type': 'alert',
            'data': alert
        })

class SlackNotifier:
    """Send alerts to Slack webhook"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send(self, alert: Dict[str, Any]):
        """Send alert to Slack"""
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json={
                'text': f"*{alert['severity'].upper()}*: {alert['rule_name']}\n"
                        f"Stream: {alert['event']['stream_id']}\n"
                        f"Time: {alert['triggered_at']}"
            })

class EmailNotifier:
    """Send alerts via email"""
    
    def __init__(self, smtp_config: Dict, recipients: List[str]):
        self.smtp_config = smtp_config
        self.recipients = recipients
        
    async def send(self, alert: Dict[str, Any]):
        """Send email alert (async wrapper around SMTP)"""
        # Implementation would use aiosmtplib
        pass
```

---

## 3. Real-Time WebSocket Dashboard

```python
# src/streaming/dashboards/websocket_manager.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json

class WebSocketConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, client_data: Dict = None):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = client_data or {}
        
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
            
    async def send_personal(self, message: Dict, websocket: WebSocket):
        """Send message to specific client"""
        await websocket.send_json(message)
        
    async def broadcast(self, message: Dict, exclude: WebSocket = None):
        """Broadcast to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            if connection == exclude:
                continue
                
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
            
    async def broadcast_to_stream(self, stream_id: str, message: Dict):
        """Broadcast to clients watching a specific stream"""
        for connection, data in self.connection_data.items():
            if data.get('stream_id') == stream_id:
                try:
                    await connection.send_json(message)
                except WebSocketDisconnect:
                    self.disconnect(connection)

# FastAPI WebSocket endpoint
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()
manager = WebSocketConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time video analytics"""
    
    # Accept connection with stream subscription
    await manager.connect(websocket, {'client_id': client_id})
    
    try:
        while True:
            # Receive client messages (e.g., subscribe to stream)
            data = await websocket.receive_json()
            
            if data['type'] == 'subscribe':
                stream_id = data['stream_id']
                manager.connection_data[websocket]['stream_id'] = stream_id
                
                await manager.send_personal({
                    'type': 'subscribed',
                    'stream_id': stream_id,
                    'message': f'Subscribed to stream {stream_id}'
                }, websocket)
                
            elif data['type'] == 'query':
                # Handle queries over WebSocket
                query = data['query']
                # Process query and send results
                results = await process_query(query)
                await manager.send_personal({
                    'type': 'query_results',
                    'results': results
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/dashboard/{stream_id}")
async def get_dashboard(stream_id: str):
    """Serve real-time dashboard HTML"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Real-Time Video Analytics - {stream_id}</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            #video-container {{ width: 100%; max-width: 800px; }}
            #events {{ height: 300px; overflow-y: scroll; }}
            .alert-critical {{ color: red; font-weight: bold; }}
            .alert-warning {{ color: orange; }}
        </style>
    </head>
    <body>
        <h1>Video Analytics Dashboard - {stream_id}</h1>
        
        <div id="video-container">
            <img id="video-frame" src="" alt="Live stream">
        </div>
        
        <div>
            <canvas id="metrics-chart"></canvas>
        </div>
        
        <div id="events">
            <h3>Real-Time Events</h3>
            <div id="event-list"></div>
        </div>
        
        <div id="alerts">
            <h3>Alerts</h3>
            <div id="alert-list"></div>
        </div>
        
        <script>
            const ws = new WebSocket(`ws://localhost:8000/ws/client1`);
            const streamId = '{stream_id}';
            
            ws.onopen = () => {{
                ws.send(JSON.stringify({{
                    type: 'subscribe',
                    stream_id: streamId
                }}));
            }};
            
            ws.onmessage = (event) => {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'frame') {{
                    document.getElementById('video-frame').src = `data:image/jpeg;base64,${{data.frame}}`;
                }}
                else if (data.type === 'event') {{
                    const eventList = document.getElementById('event-list');
                    const eventDiv = document.createElement('div');
                    eventDiv.textContent = `${{data.event_type}} at ${{new Date(data.timestamp).toLocaleTimeString()}} - Confidence: ${{data.confidence}}`;
                    eventList.prepend(eventDiv);
                    
                    // Keep only last 50 events
                    while (eventList.children.length > 50) {{
                        eventList.removeChild(eventList.lastChild);
                    }}
                }}
                else if (data.type === 'alert') {{
                    const alertList = document.getElementById('alert-list');
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `alert-${{data.severity}}`;
                    alertDiv.textContent = `🔔 ${{data.rule_name}} - ${{data.severity.toUpperCase()}} at ${{new Date(data.triggered_at).toLocaleTimeString()}}`;
                    alertList.prepend(alertDiv);
                }}
                else if (data.type === 'metrics') {{
                    updateChart(data.metrics);
                }}
            }};
            
            // Real-time chart
            const ctx = document.getElementById('metrics-chart').getContext('2d');
            const chart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: [],
                    datasets: [
                        {{ label: 'Events/sec', data: [], borderColor: 'blue' }},
                        {{ label: 'Objects detected', data: [], borderColor: 'green' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    animation: false
                }}
            }});
            
            function updateChart(metrics) {{
                const now = new Date().toLocaleTimeString();
                chart.data.labels.push(now);
                chart.data.datasets[0].data.push(metrics.events_per_second);
                chart.data.datasets[1].data.push(metrics.objects_detected);
                
                // Keep last 60 points
                if (chart.data.labels.length > 60) {{
                    chart.data.labels.shift();
                    chart.data.datasets.forEach(dataset => dataset.data.shift());
                }}
                
                chart.update();
            }}
        </script>
    </body>
    </html>
    """)
```

---

## 4. Integration with FastAPI Routes

```python
# src/backend/api/routes/streaming_routes.py
from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket
from typing import List, Optional
import asyncio
from ...streaming.ingesters import RTMPIngester
from ...streaming.processors import StreamProcessor
from ...streaming.alerts import AlertEngine, create_alert_rules
from ...streaming.dashboards import WebSocketConnectionManager

router = APIRouter(prefix="/api/v1/streaming", tags=["streaming"])

# Global components
alert_engine = AlertEngine(notifiers=[])
for rule in create_alert_rules():
    alert_engine.add_rule(rule)

manager = WebSocketConnectionManager()

@router.post("/streams/start")
async def start_stream_ingestion(
    stream_url: str,
    stream_id: str,
    format: str = "rtmp"
):
    """Start ingesting a live stream"""
    
    if format == "rtmp":
        ingester = RTMPIngester(
            stream_url=stream_url,
            topic=f"video-stream-{stream_id}",
            bootstrap_servers=["localhost:9092"]
        )
        
        # Start ingester in background
        asyncio.create_task(ingester.start())
        
        return {
            "status": "started",
            "stream_id": stream_id,
            "message": f"Started ingesting {stream_url}"
        }
    else:
        raise HTTPException(400, f"Unsupported format: {format}")

@router.post("/streams/{stream_id}/process")
async def start_stream_processing(stream_id: str):
    """Start real-time processing for a stream"""
    
    processor = StreamProcessor(
        stream_id=stream_id,
        alert_engine=alert_engine,
        websocket_manager=manager
    )
    
    asyncio.create_task(processor.process())
    
    return {
        "status": "processing",
        "stream_id": stream_id
    }

@router.get("/streams/{stream_id}/metrics")
async def get_stream_metrics(stream_id: str):
    """Get real-time metrics for a stream"""
    
    # This would fetch from a metrics store (Redis/InfluxDB)
    metrics = {
        "stream_id": stream_id,
        "current_fps": 30,
        "total_frames_processed": 12345,
        "events_detected": 67,
        "alerts_triggered": 5,
        "avg_processing_latency_ms": 45,
        "objects_tracked": 3
    }
    
    return metrics

@router.get("/streams/{stream_id}/alerts")
async def get_stream_alerts(
    stream_id: str,
    limit: int = 100,
    severity: Optional[str] = None
):
    """Get historical alerts for a stream"""
    
    alerts = alert_engine.alert_history
    filtered = [a for a in alerts if a['event']['stream_id'] == stream_id]
    
    if severity:
        filtered = [a for a in filtered if a['severity'] == severity]
    
    return filtered[-limit:]

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket, {'client_id': client_id})
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data['type'] == 'subscribe':
                stream_id = data['stream_id']
                manager.connection_data[websocket]['stream_id'] = stream_id
                
                await manager.send_personal({
                    'type': 'subscribed',
                    'stream_id': stream_id
                }, websocket)
                
            elif data['type'] == 'unsubscribe':
                manager.connection_data[websocket].pop('stream_id', None)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

---

## 5. Docker Compose for Streaming Infrastructure

```yaml
# docker-compose.yml (extended for streaming)
version: '3.8'

services:
  # Existing services...
  
  # Apache Kafka for stream processing
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
      
  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      
  # Apache Flink for stream processing
  jobmanager:
    image: flink:latest
    ports:
      - "8081:8081"
    command: jobmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=jobmanager
      
  taskmanager:
    image: flink:latest
    depends_on:
      - jobmanager
    command: taskmanager
    environment:
      - JOB_MANAGER_RPC_ADDRESS=jobmanager
      
  # Redis for real-time state and caching
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis-data:/data
      
  # InfluxDB for time-series metrics
  influxdb:
    image: influxdb:2.0
    ports:
      - "8086:8086"
    environment:
      - INFLUXDB_DB=video_analytics
      - INFLUXDB_ADMIN_USER=admin
      - INFLUXDB_ADMIN_PASSWORD=password
    volumes:
      - influxdb-data:/var/lib/influxdb2
      
  # Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - influxdb
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      
  # RTMP server for live streaming (optional)
  nginx-rtmp:
    image: tiangolo/nginx-rtmp
    ports:
      - "1935:1935"  # RTMP
      - "8080:80"    # HLS
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      
volumes:
  redis-data:
  influxdb-data:
  grafana-data:
```

---

## 6. Main Entry Point for Streaming

```python
# main.py (updated with streaming support)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from src.backend.api.routes import video_routes, query_routes, streaming_routes
from src.streaming.processors import StreamOrchestrator

app = FastAPI(title="Visi-Agent Streaming Analytics", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(video_routes.router)
app.include_router(query_routes.router)
app.include_router(streaming_routes.router)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    logging.info("Starting Visi-Agent Streaming Analytics System")
    
    # Start stream orchestrator
    orchestrator = StreamOrchestrator()
    asyncio.create_task(orchestrator.run())
    
@app.get("/")
async def root():
    return {
        "name": "Visi-Agent Streaming Analytics",
        "version": "2.0.0",
        "features": [
            "Real-time video stream ingestion",
            "Live event detection and alerting",
            "WebSocket dashboard",
            "Temporal video RAG",
            "Batch processing for archived videos"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "mode": "streaming"}
```

---

## 7. Performance Optimizations for Streaming

```python
# src/processing/streaming_models/quantization.py
import torch
from transformers import AutoModelForImageClassification

class ModelOptimizer:
    """Optimize models for real-time inference"""
    
    @staticmethod
    def quantize_model(model_path: str, output_path: str):
        """Quantize model to INT8 for faster inference"""
        model = torch.load(model_path)
        model.eval()
        
        # Dynamic quantization
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {torch.nn.Linear},
            dtype=torch.qint8
        )
        
        torch.save(quantized_model, output_path)
        return quantized_model
    
    @staticmethod
    def optimize_for_edge(model, target_fps: int = 30):
        """Optimize model for edge deployment"""
        # Prune unimportant weights
        # Or use ONNX runtime
        import onnx
        import onnxruntime
        
        # Convert to ONNX
        dummy_input = torch.randn(1, 3, 224, 224)
        torch.onnx.export(
            model,
            dummy_input,
            "model.onnx",
            opset_version=11,
            do_constant_folding=True
        )
        
        # Use ONNX Runtime with optimization
        session = onnxruntime.InferenceSession(
            "model.onnx",
            providers=['CPUExecutionProvider']
        )
        
        return session

# Use TensorRT for GPU acceleration
class TensorRTEngine:
    """TensorRT optimization for NVIDIA GPUs"""
    
    def __init__(self, model_path: str):
        import tensorrt as trt
        
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)
        
        # Load engine
        with open(model_path, 'rb') as f:
            self.engine = self.runtime.deserialize_cuda_engine(f.read())
            
        self.context = self.engine.create_execution_context()
        
    def infer(self, input_tensor):
        """Run inference with TensorRT"""
        # Bindings for input/output
        bindings = [int(input_tensor.data_ptr())]
        
        # Execute
        self.context.execute_v2(bindings)
        
        return output_tensor
```

---

## Summary: Key Enhancements for Streaming

| Component | Batch RAG | Streaming Analytics |
|-----------|-----------|---------------------|
| **Ingestion** | File upload | RTMP/WebRTC/Kafka streams |
| **Processing** | Single pass | Continuous windows |
| **Storage** | Vector DB | Kafka + Time-series DB |
| **Query** | Manual | Real-time alerts + WebSocket |
| **Models** | Large (GPT-4V) | Lightweight (YOLO/MobileNet) |
| **Latency** | Seconds to minutes | < 100ms |
| **Scale** | Single video | Multiple concurrent streams |

## Next Steps to Implement

1. **Week 1:** Set up Kafka and implement RTMP ingester
2. **Week 2:** Build Flink streaming processor with windowing
3. **Week 3:** Implement real-time event detection with YOLO
4. **Week 4:** Create alert engine and WebSocket dashboard
5. **Week 5:** Add time-series metrics with InfluxDB/Grafana
6. **Week 6:** Optimize models with quantization and TensorRT

Would you like me to provide more detailed implementation for any specific streaming component, such as the Kafka producer/consumer patterns, Flink windowing strategies, or WebSocket load balancing?
