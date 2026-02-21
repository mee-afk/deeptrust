#!/bin/bash

echo "Creating DeepTrust directory structure..."

# Backend structure
mkdir -p backend/services/{auth,analysis,models,gateway}/app/{routes,services,utils}
mkdir -p backend/services/auth/app/models
mkdir -p backend/services/auth/tests
mkdir -p backend/services/analysis/app/{workers,models}
mkdir -p backend/services/analysis/tests
mkdir -p backend/services/models/app/{models,weights}
mkdir -p backend/services/models/tests
mkdir -p backend/services/gateway/app/middleware
mkdir -p backend/services/gateway/tests
mkdir -p backend/shared/{database,models,schemas,utils}
mkdir -p backend/scripts

# Frontend structure
mkdir -p frontend/src/{components/{common,layout,auth,analysis},pages/Admin,services,store/slices,hooks,utils,routes,assets/{images,icons}}
mkdir -p frontend/public

# Infrastructure
mkdir -p infrastructure/{terraform/modules/{vpc,eks,rds},kubernetes/{deployments,services,ingress,configmaps},docker/{nginx,postgres},monitoring/{grafana/dashboards}}

# ML
mkdir -p ml/{notebooks,training/config,data/{raw,processed,datasets},evaluation}

# Tests
mkdir -p tests/{e2e,integration,performance}

# Docs
mkdir -p docs/{api,architecture/diagrams,deployment,user_guide}

# GitHub workflows
mkdir -p .github/workflows

echo "✓ Directory structure created!"

# Create essential files
touch backend/services/auth/app/__init__.py
touch backend/services/analysis/app/__init__.py
touch backend/services/models/app/__init__.py
touch backend/services/gateway/app/__init__.py
touch backend/shared/__init__.py

# Create README files
echo "# DeepTrust - AI Deepfake Detection System" > README.md
echo "# Backend Services" > backend/README.md
echo "# Frontend Application" > frontend/README.md

echo "✓ Essential files created!"
echo ""
echo "Next steps:"
echo "1. Run: chmod +x setup.sh"
echo "2. Run: ./setup.sh"
echo "3. Follow the guide to create configuration files"

