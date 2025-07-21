# Migration Guardian

🛡️ **Automatic database migration safety and generation for FastAPI + SQLAlchemy + Alembic projects**

Migration Guardian is a Claude Code hook that monitors SQLAlchemy model changes in your modular architecture and automatically:
- Detects model changes across all modules
- Generates safe Alembic migrations
- Analyzes risks and data impact
- Detects cross-module dependencies
- Provides safety recommendations

## 🚀 Quick Start

### Installation

1. Migration Guardian is already registered in `.claude/settings.json`
2. Configuration is managed in `hooks/migration_guardian_config.json`

### Usage

Migration Guardian automatically activates when you modify any file matching these patterns:
- `app/*/models/*.py` (any module)
- `app/*/models/**/*.py` (nested models)
- `app/core/models/*.py`
- `app/shared/models/*.py`

## 📋 Features

### 1. Automatic Model Change Detection
- Detects new tables, columns, and constraints
- Identifies removed fields and tables
- Tracks type changes and nullable modifications
- Monitors index and foreign key changes

### 2. Modular Architecture Support
- Automatically discovers new modules
- Prefixes migrations with module names
- Tracks cross-module dependencies
- Generates dependency-aware migration order

### 3. Safety Analysis
- Risk assessment (LOW/MEDIUM/HIGH)
- Data loss warnings
- Performance impact estimation
- Rollback difficulty analysis

### 4. Smart Migration Generation
- Auto-generates Alembic migrations
- Adds comprehensive safety comments
- Creates staged migrations for complex changes
- Includes rollback scripts for dangerous operations

### 5. Cross-Module Dependency Detection
- Maps foreign key relationships
- Calculates correct migration order
- Warns about circular dependencies
- Generates dependency graphs

## 🔧 Configuration

Edit `hooks/migration_guardian_config.json` to customize behavior:

```json
{
  "auto_generate": true,          // Auto-generate migrations
  "require_review": true,         // Require user confirmation
  "block_dangerous": false,       // Block HIGH risk operations
  "analyze_data_impact": true,    // Check affected row counts
  
  "monitored_paths": [            // Paths to monitor
    "app/*/models/*.py",
    "app/*/models/**/*.py",
    "app/core/models/*.py",
    "app/shared/models/*.py"
  ],
  
  "safety_thresholds": {
    "max_affected_rows_auto": 1000,      // Max rows for auto-approval
    "require_backup_above_rows": 10000,  // Backup threshold
    "require_staged_migration_above": 100000  // Staging threshold
  }
}
```

## 📊 Risk Levels

### ✅ LOW Risk
- Adding nullable columns
- Creating new tables
- Adding indexes
- Safe constraint additions

### ⚠️ MEDIUM Risk  
- Adding NOT NULL columns without defaults
- Type conversions
- Adding unique constraints
- Modifying nullable status

### 🔴 HIGH Risk
- Dropping tables
- Dropping columns
- Removing constraints
- DELETE/TRUNCATE operations

## 🎯 Example Outputs

### Safe Operation
```
✅ MIGRATION GUARDIAN: Safe Migration
════════════════════════════════════════════════════════════

📦 Module: auth
📝 Changes detected: 1

✅ Created: alembic/versions/2025_01_20_auth_add_user_verification.py

📊 Analysis:
- Operation: ADD COLUMN is_verified
- Table: users (1,234 records)
- Risk: LOW ✅
- Rollback: Simple
```

### Dangerous Operation
```
🚨 MIGRATION GUARDIAN: DANGEROUS OPERATION DETECTED!
════════════════════════════════════════════════════════════

⚠️ RISKS DETECTED:
   - DROP_COLUMN on users

🔴 WARNINGS:
   - Column data will be permanently lost
   - 987 rows contain data in this column

💡 RECOMMENDATIONS:
   - Create backup before dropping column
   - Consider renaming to phone_deprecated instead

🛡️ SAFETY CHECKLIST:
   [ ] Database backup created
   [ ] Tested on staging environment
   [ ] Downtime window scheduled
   [ ] Rollback plan prepared
   [ ] Team notified of changes

⚠️ Proceed with migration generation? [y/N]:
```

## 🔍 Module Detection

Migration Guardian automatically detects your module structure:

```
app/
├── auth/
│   └── models/
│       ├── user.py         # Detected: auth module
│       └── session.py
├── files/
│   └── models/
│       └── file.py         # Detected: files module
└── payments/               # New module!
    └── models/
        └── payment.py      # Auto-detected!
```

## 🚦 Migration Staging

For complex changes, Migration Guardian creates staged migrations:

```
alembic/versions/
├── 2025_01_20_auth_complex_change_staged/
│   ├── step1_add_temp_columns.py
│   ├── step2_migrate_data.py
│   ├── step3_apply_constraints.py
│   └── step4_cleanup_old_columns.py
```

## 📝 Generated Migration Example

```python
"""
Migration Guardian Analysis
==========================

Module: auth
Risk Level: ⚠️ MEDIUM
Generated: 2025-01-20 15:30:00

Changes Summary:
---------------
- ADD_COLUMN: users.is_verified
- ALTER_COLUMN_NULLABLE: users.email

Affected Data:
--------------
- users: 1,234 rows

Cross-Module Dependencies:
-------------------------
- files → auth (users.id)

⚠️ WARNINGS:
----------
- Setting column to NOT NULL will fail if NULL values exist

💡 RECOMMENDATIONS:
----------------
- UPDATE users SET email = '<default>' WHERE email IS NULL;

SAFETY CHECKLIST:
----------------
[ ] Backup completed
[ ] Tested on staging
"""

def upgrade():
    # Migration Guardian Safety Checks
    # ⚠️ BACKUP REQUIRED - Large number of rows affected
    
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.alter_column('users', 'email', nullable=False)
```

## 🛠️ Interactive Commands

When Migration Guardian is active, you can use these commands:

```bash
"Migration Guardian, analyze pending migrations"
"Migration Guardian, check production compatibility"
"Migration Guardian, estimate migration time"
"Migration Guardian, generate rollback script"
```

## 📊 Reports

Migration Guardian saves detailed reports in:
- `migration_guardian_reports/YYYY_MM_DD_HHMMSS_analysis.json`
- `migration_guardian_reports/YYYY_MM_DD_HHMMSS_analysis.md`

## 🚨 Emergency Rollback

For HIGH risk operations, Migration Guardian generates rollback scripts:

```sql
-- migration_guardian_reports/rollback_scripts/2025_01_20_emergency_rollback.sql

-- Restore dropped column data
INSERT INTO users (id, phone)
SELECT id, phone FROM users_phone_backup;

-- Re-create dropped constraints
ALTER TABLE orders ADD CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id);
```

## 🔧 Troubleshooting

### Hook not triggering?
1. Check file path matches patterns in `monitored_paths`
2. Verify hook is registered in `.claude/settings.json`
3. Check logs in `logs/migration_guardian_*.log`

### Migration generation fails?
1. Ensure Alembic is properly configured
2. Check database connection in `alembic.ini`
3. Verify module has proper `__init__.py` files

### False positives?
- Adjust `dangerous_operations` in config
- Modify `safety_thresholds` for your data scale

## 📚 Best Practices

1. **Always test on staging** - Even "safe" migrations can have issues
2. **Review generated migrations** - Migration Guardian adds safety, not perfection
3. **Keep backups current** - Especially before HIGH risk operations
4. **Use staged migrations** - For complex multi-step changes
5. **Monitor after deployment** - Watch for performance impacts

## 🤝 Contributing

Migration Guardian is part of your project. Feel free to modify:
- Add custom safety rules
- Enhance risk detection
- Integrate with your backup system
- Add project-specific checks

## 📄 License

Same as your project license.