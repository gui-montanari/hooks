"""
Output formatters for Migration Guardian
"""

from datetime import datetime
from typing import Dict, List, Any


def format_alert(safety_report: Dict[str, Any]) -> str:
    """Format safety alert for display"""
    risk_level = safety_report['risk_level']
    
    if risk_level == 'HIGH':
        header = "🚨 MIGRATION GUARDIAN: DANGEROUS OPERATION DETECTED!"
    elif risk_level == 'MEDIUM':
        header = "⚠️  MIGRATION GUARDIAN: CAUTION REQUIRED"
    else:
        header = "✅ MIGRATION GUARDIAN: Safe Migration"
        
    output = [
        "",
        "="*60,
        header,
        "="*60,
        ""
    ]
    
    # Add risks
    if safety_report.get('risks'):
        output.append("⚠️  RISKS DETECTED:")
        for risk in safety_report['risks']:
            change = risk['change']
            output.append(f"   - {change['type']} on {change.get('table', 'unknown')}")
            
        output.append("")
        
    # Add warnings
    if safety_report.get('warnings'):
        output.append("🔴 WARNINGS:")
        for warning in safety_report['warnings']:
            output.append(f"   - {warning}")
        output.append("")
        
    # Add data impact
    if safety_report.get('data_impact'):
        output.append("📊 DATA IMPACT:")
        for table, impact in safety_report['data_impact'].items():
            if impact['has_data']:
                output.append(f"   - {table}: {impact['row_count']:,} rows affected")
        output.append("")
        
    # Add recommendations
    if safety_report.get('recommendations'):
        output.append("💡 RECOMMENDATIONS:")
        for rec in safety_report['recommendations']:
            output.append(f"   - {rec}")
        output.append("")
        
    # Add safety checklist for dangerous operations
    if risk_level == 'HIGH':
        output.extend([
            "🛡️  SAFETY CHECKLIST:",
            "   [ ] Database backup created",
            "   [ ] Tested on staging environment", 
            "   [ ] Downtime window scheduled",
            "   [ ] Rollback plan prepared",
            "   [ ] Team notified of changes",
            ""
        ])
        
    output.append("="*60)
    
    return '\n'.join(output)


def format_report(report_data: Dict[str, Any]) -> str:
    """Format comprehensive report as markdown"""
    timestamp = report_data['timestamp']
    module = report_data['module']
    changes = report_data['changes']
    dependencies = report_data['dependencies']
    safety_report = report_data['safety_report']
    migrations = report_data['migrations']
    
    md = [
        f"# Migration Guardian Report",
        f"**Date**: {timestamp}",
        f"**Module**: {module}",
        "",
        "## Summary",
        f"- **Changes Detected**: {len(changes['changes'])}",
        f"- **Migrations Generated**: {len(migrations)}",
        f"- **Risk Level**: {safety_report['risk_level']}",
        f"- **Cross-Module Dependencies**: {'Yes' if dependencies['cross_module'] else 'No'}",
        ""
    ]
    
    # Changes detail
    md.extend([
        "## Changes Detail",
        "",
        "| Type | Table | Details | Risk |",
        "|------|-------|---------|------|"
    ])
    
    for change in changes['changes']:
        change_type = change['type']
        table = change.get('table', '-')
        details = _format_change_details(change)
        risk = change.get('risk', 'LOW')
        
        md.append(f"| {change_type} | {table} | {details} | {risk} |")
        
    md.append("")
    
    # Dependencies
    if dependencies['cross_module']:
        md.extend([
            "## Cross-Module Dependencies",
            ""
        ])
        
        for dep in dependencies['dependencies']:
            md.append(
                f"- **{dep['from_module']}** → **{dep['to_module']}** "
                f"({dep['type']}: {dep['reference']})"
            )
            
        md.extend([
            "",
            "### Migration Order",
            f"Apply migrations in this order: {' → '.join(dependencies['migration_order'])}",
            ""
        ])
        
    # Safety Analysis
    md.extend([
        "## Safety Analysis",
        "",
        f"**Overall Risk**: {safety_report['risk_level']}",
        ""
    ])
    
    if safety_report.get('warnings'):
        md.append("### Warnings")
        for warning in safety_report['warnings']:
            md.append(f"- ⚠️  {warning}")
        md.append("")
        
    if safety_report.get('recommendations'):
        md.append("### Recommendations")
        for rec in safety_report['recommendations']:
            md.append(f"- 💡 {rec}")
        md.append("")
        
    # Data Impact
    if safety_report.get('data_impact'):
        md.extend([
            "### Data Impact",
            "",
            "| Table | Rows | Size (MB) |",
            "|-------|------|-----------|"
        ])
        
        for table, impact in safety_report['data_impact'].items():
            rows = impact.get('row_count', 0)
            size = impact.get('data_size', 0)
            md.append(f"| {table} | {rows:,} | {size} |")
            
        md.append("")
        
    # Generated Migrations
    md.extend([
        "## Generated Migrations",
        ""
    ])
    
    for i, migration in enumerate(migrations, 1):
        risk_emoji = {'LOW': '✅', 'MEDIUM': '⚠️', 'HIGH': '🚨'}
        emoji = risk_emoji.get(migration.get('risk_level', 'LOW'), '✅')
        
        md.append(f"{i}. {emoji} `{migration['filename']}`")
        
        if migration.get('warnings'):
            for warning in migration['warnings']:
                md.append(f"   - {warning}")
                
    md.extend([
        "",
        "## Next Steps",
        "",
        "1. Review the generated migration files",
        "2. Test migrations on a staging database",
        "3. Create database backup if needed",
        "4. Apply migrations in the recommended order",
        "5. Monitor application after deployment",
        ""
    ])
    
    # Add SQL snippets for dangerous operations
    if safety_report['risk_level'] == 'HIGH':
        md.extend([
            "## Emergency Rollback SQL",
            "",
            "```sql",
            "-- Save this for emergency rollback",
            ""
        ])
        
        for change in changes['changes']:
            if change['type'] == 'DROP_COLUMN':
                md.append(
                    f"-- Before dropping {change['table']}.{change['column']}:"
                )
                md.append(
                    f"CREATE TABLE {change['table']}_{change['column']}_backup AS "
                    f"SELECT id, {change['column']} FROM {change['table']};"
                )
                
        md.extend(["```", ""])
        
    return '\n'.join(md)


def _format_change_details(change: Dict[str, Any]) -> str:
    """Format change details for table display"""
    details = []
    
    if 'column' in change:
        details.append(f"Column: {change['column']}")
        
    if 'column_type' in change:
        details.append(f"Type: {change['column_type']}")
        
    if 'old_type' in change and 'new_type' in change:
        details.append(f"{change['old_type']} → {change['new_type']}")
        
    if 'nullable' in change:
        details.append(f"Nullable: {change['nullable']}")
        
    if 'foreign_key' in change:
        details.append(f"FK: {change['foreign_key']}")
        
    return ', '.join(details) if details else '-'