// Compatibility entry point. Explicit --live and --session-dir remain required.
if(!process.argv.includes('--live'))throw Error('Requires --live');
await import('./command_center_check.mjs');
