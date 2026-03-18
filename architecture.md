finagent-systems/
├── fin_agent/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── tools.py        # Piyasa verisi çekme, PDF ayrıştırma araçları
│   │   ├── nodes.py        # Orchestrator, FVA, MIA ve RAA node fonksiyonları
│   │   └── state.py        # Graph state tanımı (Paylaştığın örnekteki gibi)
│   ├── __init__.py
│   └── agent.py            # Graph'ın (StateGraph) kurgulandığı ve derlendiği yer
├── proto/                  # Banka içi gRPC tanımları (Core banking iletişimi için)
├── .env                    # Vertex AI ve API anahtarları       
├── langgraph.json          # LangGraph Cloud/Studio konfigürasyonu
├── docker-compose.yml
├── .gitignore
├── .terraform.lock.cl
├── gcp-key.json
├── langgraph.json
├── main.tf
├── requirements.txt
├── terraform.tfstate
└── terraform.tfstate.backup