# Roadmap

> **Project Vision:** Create the definitive open-source tool for converting physical media collections into organized digital archives.

## Current Status: v0.9.0-beta

**Digital Archive Maker** is feature-complete for core use cases and has undergone extensive testing and validation. This roadmap outlines the path to a stable 1.0.0 release and beyond.

---

## 🎯 v1.0.0 Release Goals

### Stability & Reliability
- [ ] **Hardware Compatibility Testing**
  - Test with multiple optical drive models

- [ ] **API Graceful Failure Improvements**
  - Verify missing API key fallback and error messaging
  - Verify consistent timeout and retry behavior across all APIs

- [ ] **User Experience Refinements**
  - Add rip time estimate display
  - Improve and standardize progress indicators
  - Standardize error message formatting and user guidance across all scripts
  - Complete GUI application testing and refinement

### Documentation & Onboarding
- [ ] **Documentation Polish**
  - Add troubleshooting guide for common issues
  - Create video tutorials for key workflows
  - Expand FAQ with real user scenarios

- [ ] **Examples Gallery**
  - Sample library structures
  - Configuration examples for different setups
  - Integration examples with various media servers

---

## 🚀 Post-1.0.0 Vision

### v1.1.0 - Enhanced User Experience
- **Workflow Integration - "Process Once, Done Forever"**
  - Verify one-shot enhanced CD ripping with automatic quality checks and metadata repair
  - Verify one-shot video ripping with automatic TMDb metadata and ratings fetching
  - 🔄 TV show processing workflow with CLI integration (`make rip-episodes`) - **ripping complete, organization verification needed**
  - Lyrics fetching and explicit content tagging integrated into main workflows
- **User Experience Features**
  - Disc ripping counter with stats and milestone tracking
  - Rip time estimation: "Come back in ~28 minutes (at 3:47 PM)"
  - Storage management with automatic cleanup of intermediate files
  - Family-friendly content filtering and sync controls
- **GUI Application Maturity**
  - User experience refinements based on community feedback
  - Enhanced dashboard and console integration

---

## 🔧 Technical Priorities

### Code Quality
- **Maintain priority test coverage**
- **Zero critical security vulnerabilities**
- **Consistent code style and documentation**


### User Experience
- **Clear error messages with actionable guidance**
- **Consistent interface across components**

---

## 🤝 Community Involvement

### How to Contribute
- **Bug Reports**: Help identify edge cases and hardware issues
- **Feature Requests**: Suggest workflows and improvements
- **Documentation**: Share guides and examples
- **Code**: Submit pull requests for bug fixes and features

### Feedback Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code contributions and documentation

### Recognition
- **Contributors acknowledged in releases**
- **Feature attribution in documentation**
- **Community highlights in project updates

---

## 📅 Development Phases

| Milestone | Status |
|-----------|---------|
| v0.9.0-beta | ✅ Complete |
| v1.0.0 | 🎯 Next major release |
| v1.1.0 | 📋 Planned enhancements |
| Future versions | 💭 Ideas and possibilities |

*Development proceeds at a sustainable hobby project pace.*

---

## 🎯 Project Goals

### Quality & Reliability
- [ ] Zero critical bugs in production
- [ ] Maintain comprehensive test coverage
- [ ] Reliable hardware compatibility across common drives

### User Experience
- [ ] Clear documentation for all workflows
- [ ] Helpful error messages with actionable guidance
- [ ] Smooth setup process for new users

---

## 🔄 Release Process

### Beta Releases (v0.9.x)
- **Incremental updates** with bug fixes and small features
- **Community testing** and feedback incorporation
- **Documentation updates** and improvements

### Release Candidate (v1.0.0-rc)
- **Feature freeze** - only bug fixes allowed
- **Extensive testing** across hardware configurations
- **Final documentation review**

### Stable Release (v1.0.0)
- **Production-ready** with comprehensive testing
- **Long-term support** for stability fixes
- **Migration path** for future major versions

---

## 📋 Decision Log

### Why CLI First?
- **Scriptability** for power users and automation
- **Reliability** - fewer failure points than GUI
- **Foundation** for GUI and web interfaces

### Why macOS Initially?
- **Developer platform** - I use a Mac for development
- **Unix foundation** - for possible porting to Linux later
- **Hardware access** - good support for optical drives
- **Development efficiency** - consistent environment

### Why Open Source?
- **Community trust** - transparent development process
- **Collaboration** - leverage community expertise
- **Longevity** - project can outlive original author
- **Learning** - educational value for contributors

---

## 🚀 Getting Involved

### For Developers
- **Start with good first issues** on GitHub
- **Review the contributing guide** for development setup
- **Join discussions** to understand project direction

### For Users
- **Test the beta** and provide feedback
- **Share your experiences** and use cases
- **Report issues** with detailed reproduction steps

### For Organizations
- **Sponsor development** for specific features
- **Provide testing resources** and hardware
- **Contribute enterprise requirements**

---

*This roadmap is a living document and will evolve based on community feedback, technical discoveries, and user needs. All dates are targets and subject to change.*
