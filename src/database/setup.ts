import fs from 'fs';
import path from 'path';
import db from './config';

export function initializeDatabase(): void {
    const migrationPath = path.join(__dirname, 'migrations', '001_initial_schema.sql');
    const migrationSQL = fs.readFileSync(migrationPath, 'utf8');
    
    const statements = migrationSQL
        .split(';')
        .map(stmt => stmt.trim())
        .filter(stmt => stmt.length > 0);
    
    const transaction = db.transaction(() => {
        for (const statement of statements) {
            db.exec(statement);
        }
    });
    
    try {
        transaction();
        console.log('Database initialized successfully');
    } catch (error) {
        console.error('Failed to initialize database:', error);
        throw error;
    }
}

export function closeDatabase(): void {
    db.close();
}