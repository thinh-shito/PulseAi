#!/bin/bash

# This script generates the complete NestJS backend structure
# Run with: bash generate-nestjs-structure.sh

set -e

echo "🚀 Generating NestJS backend structure..."

# Create directory structure
mkdir -p src/core/security
mkdir -p src/domain/models
mkdir -p src/domain/phi-filter
mkdir -p src/infra/repositories
mkdir -p src/modules/auth/dto
mkdir -p src/modules/user/dto
mkdir -p src/modules/workflow/dto
mkdir -p src/modules/admin/dto
mkdir -p src/modules/chat/dto
mkdir -p src/modules/presence/dto
mkdir -p src/modules/templates/dto
mkdir -p src/common/decorators
mkdir -p src/common/guards
mkdir -p src/common/interceptors
mkdir -p src/common/filters

echo "✅ Directory structure created"

# Note: Individual file creation would follow here
# For now, this creates the directory skeleton

echo "📝 Next steps:"
echo "1. Install dependencies: npm install"
echo "2. Implement remaining TypeScript files (see NESTJS_MIGRATION_PLAN.md)"
echo "3. Remove Python code after implementation is complete"
echo ""
echo "✨ Directory structure ready for implementation"