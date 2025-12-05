# Development Guide

This document consolidates all development setup, testing, troubleshooting, and maintenance guides for the pi-tft-dfplayer project.

## Development Environment Setup

### Repository Structure
```
pi-tft-dfplayer-main/
├── src/
│   ├── app.py                     # Main application (ScreenManagerV2)
│   ├── main.py                    # Entry point
│   ├── core/                      # Configuration, state, events
│   ├── hardware/                  # Display, touch, DFPlayer
│   ├── backends/                  # Playback backends
│   └── ui/                        # UI framework and screens
├── tests/                         # Test suite
├── config/                        # Configuration files
├── systemd/                       # System services
├── scripts/                       # Setup and utility scripts
├── themes/                        # UI themes
├── docs/                          # Documentation
└── requirements*.txt              # Dependencies
```

### Prerequisites Installation

#### System Dependencies
```bash
# Install Python dependencies
./scripts/install_prereqs.sh

# Apply system configuration (frees UART0, sets up udev)
sudo ./scripts/apply_system_tweaks.sh
sudo reboot
```

#### Python Dependencies
```bash
# Core dependencies
pip3 install -r requirements.txt

# Test dependencies
pip3 install -r requirements-test.txt
```

### Hardware Verification
```bash
# Verify hardware access
ls /dev/fb1                    # Framebuffer device
cat /sys/class/graphics/fb1/name  # Should show ILI9486
ls /dev/input/event*           # Touch input devices
ls /dev/serial0                # UART for DFPlayer
```

## Testing Strategy

### Test Categories
1. **Unit Tests** (`tests/unit/`) - Individual component testing
2. **Integration Tests** (`tests/integration/`) - Component interaction
3. **Hardware Tests** (`tests/hardware/`) - Real hardware validation
4. **UI Tests** (`tests/ui/`) - Screen and widget testing

### Running Tests

#### Basic Test Execution
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/hardware/ -v
```

#### Test Results Interpretation
- **Unit Tests**: Should pass on any development machine
- **Integration Tests**: May require mocked hardware
- **Hardware Tests**: Require actual Raspberry Pi hardware
- **Coverage Target**: 80% overall, 90% for core modules

### Test Environment Setup
```bash
# Install test dependencies
pip3 install -r requirements-test.txt

# Run tests in isolated environment
python3 -m pytest tests/ --tb=short

# Generate coverage reports
python3 -m pytest tests/ --cov=src --cov-report=term-missing
```

## Application Execution

### Manual Testing
```bash
# Direct execution (requires hardware)
sudo -E python3 src/dfplayer_fb_gui.py

# With custom configuration
DFPLAYER_METADATA=/boot/custom_metadata.json sudo -E python3 src/main.py
```

### Systemd Service
```bash
# Install service
sudo cp systemd/dfplayer-fb.service /etc/systemd/system/
sudo systemctl daemon-reload

# Control service
sudo systemctl enable --now dfplayer-fb
sudo systemctl status dfplayer-fb
sudo systemctl restart dfplayer-fb

# View logs
sudo journalctl -u dfplayer-fb -f
sudo journalctl -u dfplayer-fb --since "1 hour ago"
```

### Debug Mode
```bash
# Enable debug logging
export DFPLAYER_DEBUG=1
sudo -E python3 src/main.py

# Touch debugging
export DFPLAYER_TOUCH_DEBUG=1
sudo -E python3 src/main.py
```

## Troubleshooting Guide

### Common Issues

#### Touch Input Problems
**Symptoms:** Touch not responding, incorrect coordinates
**Solutions:**
1. Check touch device detection: `ls /dev/input/event*`
2. Verify udev rules: `cat /etc/udev/rules.d/95-touchscreen.rules`
3. Test calibration: Run calibration screen from settings
4. Check orientation settings in config

#### Display Issues
**Symptoms:** Blank screen, corrupted display, wrong colors
**Solutions:**
1. Verify framebuffer: `ls /dev/fb1`
2. Check display connection and power
3. Test with simple framebuffer write
4. Verify RGB565 format support

#### Audio Problems
**Symptoms:** No sound, distorted audio, DFPlayer not responding
**Solutions:**
1. Check UART access: `ls /dev/serial0`
2. Verify DFPlayer power and connections
3. Test serial communication with DFPlayer
4. Check SD card format and file organization

#### Performance Issues
**Symptoms:** Slow UI, dropped frames, high CPU usage
**Solutions:**
1. Profile rendering performance
2. Check for memory leaks
3. Optimize image loading and caching
4. Reduce UI complexity if needed

### Diagnostic Scripts

#### System Snapshot
```bash
# Generate comprehensive system report
./scripts/system_snapshot.sh
```

#### Hardware Diagnostics
```bash
# Test DFPlayer communication
python3 scripts/diagnose_dfplayer.py

# Test touch input
python3 scripts/test_touch.py

# Test display output
python3 scripts/test_display.py
```

#### Log Analysis
```bash
# Check current application logs
./scripts/check_current_app_logs.sh

# Analyze performance
python3 scripts/profile_rendering.py
```

### Recovery Procedures

#### Configuration Reset
```bash
# Reset to defaults
rm ~/.dfplayer_config.json
# Restart application
```

#### Hardware Reinitialization
```bash
# Reset touch calibration
# Delete calibration data from config
# Run calibration procedure
```

#### Service Recovery
```bash
# Stop and restart service
sudo systemctl restart dfplayer-fb

# Check service health
sudo systemctl status dfplayer-fb
```

## Code Quality and Maintenance

### Code Style Standards
- Python 3.9+, 4-space indentation
- Constants in SCREAMING_SNAKE_CASE
- Small, single-purpose functions
- Hardware access wrapped in try/except
- Use v2 framework/components, no new ad-hoc forks

### Development Workflow

#### Git Workflow
```bash
# Feature development
git checkout -b feature/new-feature
# Make changes, test thoroughly
git commit -m "feat: add new feature"
git push origin feature/new-feature
# Create pull request
```

#### Code Review Checklist
- [ ] Tests pass with 80%+ coverage
- [ ] No new linting errors
- [ ] Documentation updated
- [ ] Hardware compatibility verified
- [ ] Performance impact assessed

### Performance Monitoring

#### Key Metrics
- Frame rate: Target 30 FPS
- Memory usage: < 100MB on Pi Zero 2W
- CPU usage: < 50% during normal operation
- Touch response: < 100ms latency

#### Profiling Tools
```bash
# Profile rendering performance
python3 scripts/profile_rendering.py

# Memory usage analysis
python3 -m memory_profiler src/main.py

# CPU profiling
python3 -m cProfile -s time src/main.py
```

## Deployment and Production

### Production Checklist
- [ ] All tests passing
- [ ] Hardware validation complete
- [ ] Configuration documented
- [ ] Backup procedures tested
- [ ] Monitoring/logging configured
- [ ] Rollback plan prepared

### Backup and Recovery
```bash
# Configuration backup
cp ~/.dfplayer_config.json ~/.dfplayer_config.json.backup

# Full system backup
tar -czf pi-tft-backup-$(date +%Y%m%d).tar.gz \
    ~/pi-tft-dfplayer \
    ~/.dfplayer_config.json \
    /etc/systemd/system/dfplayer-fb.service
```

### Monitoring and Alerting
- Systemd service status monitoring
- Log file analysis for errors
- Performance metric tracking
- Hardware health checks

---

*This document consolidates information from: TROUBLESHOOTING_UI_AND_PLAYBACK.md, TEST_PLAN.md, TESTING_GUIDE_BUGFIXES.md, QUICK_FIX_GUIDE.md, VERIFICATION_REPORT.md, and related development guides.*</content>
<parameter name="filePath">docs/DEVELOPMENT_GUIDE.md
