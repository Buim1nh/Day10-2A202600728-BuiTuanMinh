import json
import os
import subprocess
import threading
import time
import sys
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

# Add src to python path to import modules
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Global state for running tasks
state = {
    "active_pipeline": None,
    "logs": [],
    "lock": threading.Lock()
}

def run_pipeline_thread(script_name, pipeline_name):
    global state
    script_path = PROJECT_ROOT / "script" / script_name
    
    # Run the script using the current virtual env python or system python
    venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    
    python_cmd = str(venv_python) if venv_python.exists() else "python"
    
    with state["lock"]:
        state["active_pipeline"] = pipeline_name
        state["logs"] = [f"[System] Starting pipeline {pipeline_name}...\n"]
    
    try:
        process = subprocess.Popen(
            [python_cmd, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(PROJECT_ROOT)
        )
        
        # Read output line-by-line
        for line in iter(process.stdout.readline, ""):
            with state["lock"]:
                state["logs"].append(line)
        
        process.stdout.close()
        return_code = process.wait()
        
        with state["lock"]:
            state["logs"].append(f"\n[System] Pipeline finished with return code {return_code}.\n")
    except Exception as e:
        with state["lock"]:
            state["logs"].append(f"\n[System] Error running pipeline: {str(e)}\n")
    finally:
        with state["lock"]:
            state["active_pipeline"] = None

class WebServerHandler(SimpleHTTPRequestHandler):
    # Serve index.html for root path
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()
        
        # API endpoints
        if self.path.startswith("/api/"):
            self.handle_api_get()
        else:
            # Serve other static files normally
            return super().do_GET()
            
    def handle_api_get(self):
        global state
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        response_data = {}
        
        if self.path == "/api/status":
            response_data = {
                "raw_response": (DATA_DIR / "raw" / "crossref_response.json").exists(),
                "raw_records": (DATA_DIR / "raw" / "crossref_records.json").exists(),
                "clean_csv": (DATA_DIR / "clean" / "papers_clean.csv").exists(),
                "clean_json": (DATA_DIR / "clean" / "papers_clean.json").exists(),
                "baseline_metrics": (DATA_DIR / "results" / "baseline_metrics.json").exists(),
                "corrupted_metrics": (DATA_DIR / "results" / "corrupted_metrics.json").exists(),
                "repaired_metrics": (DATA_DIR / "results" / "repaired_metrics.json").exists(),
                "baseline_report": (DATA_DIR / "reports" / "phase1_report.md").exists(),
                "comparison_report": (DATA_DIR / "reports" / "corruption_report.md").exists(),
                "active_pipeline": state["active_pipeline"]
            }
        
        elif self.path == "/api/metrics":
            metrics = {
                "baseline": self.load_json_safe(DATA_DIR / "results" / "baseline_metrics.json"),
                "corrupted": self.load_json_safe(DATA_DIR / "results" / "corrupted_metrics.json"),
                "repaired": self.load_json_safe(DATA_DIR / "results" / "repaired_metrics.json")
            }
            response_data = metrics
            
        elif self.path == "/api/quality":
            response_data = {
                "baseline": self.load_json_safe(DATA_DIR / "quality" / "baseline_quality.json"),
                "corrupted": self.load_json_safe(DATA_DIR / "quality" / "corrupted_quality.json"),
                "repaired": self.load_json_safe(DATA_DIR / "quality" / "repaired_quality.json"),
                "freshness": self.load_json_safe(DATA_DIR / "quality" / "freshness_report.json"),
                "corrupted_freshness": self.load_json_safe(DATA_DIR / "quality" / "corrupted_freshness.json"),
                "repaired_freshness": self.load_json_safe(DATA_DIR / "quality" / "repaired_freshness.json")
            }
            
        elif self.path == "/api/logs":
            with state["lock"]:
                response_data = {
                    "active": state["active_pipeline"] is not None,
                    "pipeline": state["active_pipeline"],
                    "logs": list(state["logs"])
                }
                
        elif self.path == "/api/rubric":
            status = self.check_rubric_status()
            response_data = status
            
        else:
            response_data = {"error": "Endpoint not found"}
            
        self.wfile.write(json.dumps(response_data).encode("utf-8"))
        
    def do_POST(self):
        if self.path == "/api/run":
            self.handle_api_run()
        elif self.path == "/api/query":
            self.handle_api_query()
        else:
            self.send_response(404)
            self.end_headers()
            
    def handle_api_run(self):
        global state
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        try:
            params = json.loads(post_data)
        except Exception:
            params = {}
            
        pipeline = params.get("pipeline")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if not pipeline or pipeline not in ("phase1", "corruption_flow"):
            self.wfile.write(json.dumps({"success": False, "error": "Invalid pipeline name"}).encode("utf-8"))
            return
            
        with state["lock"]:
            if state["active_pipeline"] is not None:
                self.wfile.write(json.dumps({"success": False, "error": f"Pipeline {state['active_pipeline']} is already running"}).encode("utf-8"))
                return
        
        script_name = "run_phase1.py" if pipeline == "phase1" else "run_corruption_flow.py"
        thread = threading.Thread(target=run_pipeline_thread, args=(script_name, pipeline))
        thread.start()
        
        self.wfile.write(json.dumps({"success": True, "message": f"Pipeline {pipeline} started"}).encode("utf-8"))

    def handle_api_query(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        try:
            params = json.loads(post_data)
        except Exception:
            params = {}
            
        question = params.get("question")
        phase = params.get("phase", "baseline")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        
        if not question:
            self.wfile.write(json.dumps({"success": False, "error": "Question parameter is required"}).encode("utf-8"))
            return
            
        try:
            from core.config import load_settings
            from retrieval.index import LocalEmbeddingIndex
            from retrieval.qa import answer_question
            
            settings = load_settings()
            
            # Select path based on phase
            if phase == "corrupted":
                embeddings_path = settings.paths.corrupted_embeddings_json
            elif phase == "repaired":
                embeddings_path = settings.paths.repaired_embeddings_json
            else:
                embeddings_path = settings.paths.embeddings_json
                
            if not embeddings_path.exists():
                self.wfile.write(json.dumps({
                    "success": False, 
                    "error": f"Index files for phase '{phase}' do not exist. Please run the corresponding pipeline first."
                }).encode("utf-8"))
                return
                
            index = LocalEmbeddingIndex.load(settings, embeddings_path)
            res = answer_question(question, settings, index)
            
            self.wfile.write(json.dumps({
                "success": True,
                "answer": res.answer,
                "retrieved_titles": res.retrieved_titles,
                "retrieved_doc_ids": res.retrieved_doc_ids
            }).encode("utf-8"))
            
        except Exception as e:
            import traceback
            err_trace = traceback.format_exc()
            self.wfile.write(json.dumps({
                "success": False,
                "error": f"Error querying agent: {str(e)}",
                "trace": err_trace
            }).encode("utf-8"))

    def load_json_safe(self, path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def check_rubric_status(self):
        # Checking actual file presence to score
        has_phase1 = (DATA_DIR / "results" / "baseline_metrics.json").exists()
        has_corruption = (DATA_DIR / "results" / "corrupted_metrics.json").exists()
        has_quality = (DATA_DIR / "quality" / "baseline_quality.json").exists()
        has_report = (DATA_DIR / "reports" / "corruption_report.md").exists()
        
        checklist = [
            {
                "id": "1",
                "title": "Mục 1: Code structure và project organization (10đ)",
                "desc": "Code chia module rõ ràng, cấu trúc dễ hiểu, đặt tên hợp lý.",
                "status": "Passed" if (PROJECT_ROOT / "src" / "core").exists() else "Failed",
                "score": 10 if (PROJECT_ROOT / "src" / "core").exists() else 0
            },
            {
                "id": "2",
                "title": "Mục 2: Raw data ingestion (15đ)",
                "desc": "Fetch Crossref works, lưu raw responses & raw records.",
                "status": "Passed" if (DATA_DIR / "raw" / "crossref_records.json").exists() else "Failed",
                "score": 15 if (DATA_DIR / "raw" / "crossref_records.json").exists() else 0
            },
            {
                "id": "3",
                "title": "Mục 3: Cleaning và data modeling (15đ)",
                "desc": "Loại bỏ bản ghi rỗng, tính age_days và xây dựng text_for_embedding.",
                "status": "Passed" if (DATA_DIR / "clean" / "papers_clean.csv").exists() else "Failed",
                "score": 15 if (DATA_DIR / "clean" / "papers_clean.csv").exists() else 0
            },
            {
                "id": "4",
                "title": "Mục 4: Embedding và vector store (10đ)",
                "desc": "Tạo index ChromaDB sử dụng MiniLM, thực hiện semantic search.",
                "status": "Passed" if (DATA_DIR / "embeddings" / "papers_embeddings.json").exists() else "Failed",
                "score": 10 if (DATA_DIR / "embeddings" / "papers_embeddings.json").exists() else 0
            },
            {
                "id": "5",
                "title": "Mục 5: Agent và multi-provider LLM (10đ)",
                "desc": "Cấu hình provider abstraction (openai, gemini, custom).",
                "status": "Passed" if (PROJECT_ROOT / "src" / "retrieval" / "llm.py").exists() else "Failed",
                "score": 10 if (PROJECT_ROOT / "src" / "retrieval" / "llm.py").exists() else 0
            },
            {
                "id": "6",
                "title": "Mục 6: Evaluation và scoring (10đ)",
                "desc": "Chạy metrics đánh giá (Hit Rate, Token F1, Judge Accuracy).",
                "status": "Passed" if has_phase1 else "Failed",
                "score": 10 if has_phase1 else 0
            },
            {
                "id": "7",
                "title": "Mục 7: Data observability (10đ)",
                "desc": "Giám sát chất lượng dữ liệu, freshness check và xuất báo cáo.",
                "status": "Passed" if has_quality else "Failed",
                "score": 10 if has_quality else 0
            },
            {
                "id": "8",
                "title": "Mục 8: Corruption và comparison (10đ)",
                "desc": "Gây lỗi dữ liệu, re-evaluate và so sánh hiệu suất phục hồi.",
                "status": "Passed" if has_corruption and has_report else "Failed",
                "score": 10 if has_corruption and has_report else 0
            },
            {
                "id": "9",
                "title": "Bonus points (10đ)",
                "desc": "So sánh metrics trực quan, tự sửa đổi pyproject.toml cài đặt package.",
                "status": "Passed" if has_report else "Failed",
                "score": 10 if has_report else 0
            }
        ]
        
        total_score = sum(item["score"] for item in checklist)
        return {
            "checklist": checklist,
            "total_score": total_score
        }

def start_server(port=8000):
    server = HTTPServer(("0.0.0.0", port), WebServerHandler)
    print(f"[System] Server started at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    start_server(args.port)
