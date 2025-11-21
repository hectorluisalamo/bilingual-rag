#!/usr/bin/env python3
import httpx, sys, json

API = "http://localhost:8000/ingest/url"
docs = [
    {"url":"https://es.wikipedia.org/wiki/Arepa","lang":"es","topic":"food","country":"VE","index_name":"c300o45","max_tokens":300,"overlap":45},
    {"url":"https://www.usa.gov/es/ciudadania","lang":"es","topic":"civics","country":"US","index_name":"c300o45","max_tokens":300,"overlap":45},
]

def main():
    with httpx.Client(timeout=60) as client:
        for d in docs:
            r = client.post(API, json=d)
            if r.status_code != 200:
                print("seed warn:", d["url"], r.status_code, r.text, file=sys.stderr)
            else:
                print("seed ok:", d)
                
                
if __name__ == "__main__":
    main()
