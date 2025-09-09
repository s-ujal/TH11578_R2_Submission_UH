Project Title: “SMS & Voice-Based Navigation System for Keypad Phone Users”
Team ID: TH11578

1. Overview
      A lightweight, inclusive navigation system built for keypad and non-internet phone users at large gatherings like Simhastha.
      Visitors can get real-time directions through SMS or voice calls, with support for Hindi/English/local dialects.
      The solution ensures easy movement, safety, and accessibility for lakhs of people in complex crowded zones.

2. Problem & Solution
      Problem Statement:
         During Simhastha, millions of visitors face difficulties in finding ghats, gates, or lost family members due to complex routes,   
         poor internet connectivity, and digital illiteracy.

      Solution:
         An SMS & Voice-based navigation system that:
         Works on keypad phones without internet.
         Provides step-by-step route directions in local languages.
         Offers shuttle/volunteer alerts for lost/confused users.

3. Logic & Workflow
      Data Collection: Landmarks & routes from Google Directions + PostgreSQL.
      Processing: LLM extracts origin/destination → routing engine finds shortest path.
      Output: Directions via SMS (text) or voice call (TTS).
      User Side: Send SMS or call → receive directions.
      Admin Side: Manage landmarks/routes, monitor usage, send alerts.

4. Tech Stack
      Communication: Twilio / Exotel (SMS + Voice IVR)
      Backend: Django (Python)
      Routing Engine: Custom Graph-based Pathfinding Algorithm
      Database: PostgreSQL (landmarks & routes)
      Deployment: Hostinger (with load balancing + caching)
      AI Services: Speech-to-Text (Google STT / Whisper), Text-to-Speech (gTTS / Polly)

5. Future Scope (Final Version)
      Simhastha App Integration – Direct support within the official app.
      Real-time Crowd Monitoring – Safe re-routing based on density.
      Shuttle & Volunteer Alerts – Assign assistance for Divyangjan & elderly.
      Dynamic Signage & Smart Junctions – Display frequent paths & ease congestion.
      Smart Layout & Movement Planning – Optimize pilgrim flow to reduce crowding.
      Expansion – Rural navigation, other festivals & disaster management use.
      Exotel Integration: Backend handles all Exotel gateway requests for calls & SMS, ensuring real-time, India-number support during Mahakumbh.