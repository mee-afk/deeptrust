# DeepTrust - AI Deepfake Detection System

Enterprise-grade deepfake detection using ensemble AI methods.

## Quick Start
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop services
docker-compose -f docker-compose.dev.yml down
```

## Access Points

- Frontend: http://localhost:3000
- API Gateway: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RabbitMQ Management: http://localhost:15672 (user: deeptrust, pass: deeptrust_dev_password)
- MinIO Console: http://localhost:9001 (user: deeptrust, pass: deeptrust_dev_password)
- Grafana: http://localhost:3001 (user: admin, pass: admin)

## Documentation

See `docs/` directory for detailed documentation.

## License

MIT License
