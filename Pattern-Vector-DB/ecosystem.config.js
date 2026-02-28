module.exports = {
  apps: [
    {
      name: 'verdict-engine-v3',
      script: 'python3',
      args: '-m uvicorn src.api.web_dashboard:app --host 0.0.0.0 --port 6555',
      instances: 1,
      exec_mode: 'fork',
      max_memory_restart: '500M',
      error_file: './logs/pm2-error.log',
      out_file: './logs/pm2-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      autorestart: true,
      watch: false
    }
  ]
};
