# Content Filtering System for AI Discord Bot

This document describes the content filtering system implemented to allow the Dolphin Mistral model to handle NSFW content while blocking drug-related topics.

## 🎯 **Objective**

Configure the Dolphin Mistral 24B model to:
- ✅ **Allow NSFW content** (adult conversations, sexual topics, romance)
- ❌ **Block drug-related content** (all drug names, slang, and related terms)
- ❌ **Block violence and harassment** content
- 🛡️ **Maintain safety** while enabling appropriate adult discussions

## 📁 **Files Created/Modified**

### **New Files:**
- `content_filter.py` - Core content filtering system
- `test_content_filter.py` - Test suite for content filtering
- `README-Content-Filtering.md` - This documentation

### **Modified Files:**
- `model_manager.py` - Integrated content filtering
- `main.py` - Added content filter commands and guidelines

## 🔧 **How It Works**

### **Content Detection**
The system uses regex pattern matching to detect different types of content:

1. **Drug Content Detection:**
   - Common drug names (cocaine, heroin, marijuana, etc.)
   - Drug slang terms (dope, weed, crack, etc.)
   - Drug-related activities (dealing, using, manufacturing)
   - Drug paraphernalia terms

2. **NSFW Content Detection:**
   - Sexual terms and topics
   - Adult relationship discussions
   - Intimate conversations
   - Romantic content

3. **Violence Content Detection:**
   - Graphic violence terms
   - Weapons and harm-related content
   - Threats and intimidation

4. **Harassment Content Detection:**
   - Doxxing and stalking terms
   - Bullying and intimidation
   - Threat-related content

### **Filtering Logic**

```python
# For Dolphin model in NSFW mode:
if model_id == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free":
    if is_nsfw_mode:
        # Allow NSFW content but block drugs
        if ContentType.DRUGS in detected_types:
            return True, "Drug-related content is not allowed"
        if ContentType.NSFW in detected_types:
            return False, ""  # Allow NSFW content
    else:
        # In SFW mode, block NSFW content
        if ContentType.NSFW in detected_types:
            return True, "NSFW content only allowed in NSFW mode"
```

## 🎮 **New Commands**

### **Slash Commands:**
- `/contentfilter` - Show content filtering information
- `/modelinfo <model>` - Show detailed model information including guidelines

### **Enhanced Commands:**
- `/modelinfo dolphin` - Now shows special content guidelines for Dolphin model
- `/models` - Updated to show Dolphin model's special capabilities

## 📊 **Content Guidelines by Model**

### **Dolphin Mistral 24B (NSFW Mode):**
```
🔞 Dolphin Mistral 24B - Content Guidelines:
✅ Allowed in NSFW mode: Adult content, sexual topics, romantic discussions
❌ Never allowed: Drug-related content, violence, harassment
⚠️ Note: This model is designed for adult conversations but maintains strict boundaries against harmful content.
```

### **Other Models (Standard):**
```
🛡️ Standard Content Guidelines:
✅ Allowed: Safe-for-work content, general discussions
❌ Not allowed: NSFW content, drugs, violence, harassment
💡 Tip: Use !togglemode to enable NSFW mode for adult content.
```

## 🧪 **Testing**

Run the test suite to verify content filtering:

```bash
python test_content_filter.py
```

**Test Cases Include:**
- ✅ NSFW romantic content (allowed for Dolphin in NSFW mode)
- ❌ Drug-related content (blocked for all models)
- ❌ Violence content (blocked for all models)
- ❌ NSFW content in SFW mode (blocked)
- ✅ SFW programming content (allowed)
- ✅ Cooking content (allowed, not drug-related)

## 🔒 **Safety Features**

### **Multi-Layer Protection:**
1. **Input Filtering** - Blocks inappropriate prompts before processing
2. **Response Filtering** - Filters AI responses for inappropriate content
3. **Model-Specific Rules** - Different rules for different models
4. **Mode-Based Filtering** - Different rules for SFW vs NSFW modes

### **Blocked Content Categories:**
- **Drugs** - All drug names, slang, and related activities
- **Violence** - Graphic violence, weapons, harm
- **Harassment** - Doxxing, stalking, threats
- **NSFW in SFW mode** - Adult content outside NSFW channels

### **Allowed Content Categories:**
- **SFW Content** - Safe for work discussions
- **NSFW Content** - Adult topics in NSFW mode (Dolphin model)
- **Romantic Discussions** - Dating, relationships, intimacy
- **Educational Content** - Learning and information sharing

## 🚀 **Usage Instructions**

### **For Users:**
1. **Enable NSFW Mode** (Admin only):
   ```
   !togglemode
   ```

2. **Verify Age** (Required for NSFW):
   ```
   /attest
   ```

3. **Switch to Dolphin Model**:
   ```
   /model dolphin
   ```

4. **View Content Guidelines**:
   ```
   /contentfilter
   /modelinfo dolphin
   ```

### **For Administrators:**
1. **Enable NSFW Mode** for the server
2. **Ensure users attest** they are 18+
3. **Monitor content** using the filtering system
4. **Review guidelines** with `/contentfilter`

## 📈 **Benefits**

### **Enhanced Safety:**
- Prevents drug-related content while allowing adult conversations
- Maintains platform safety and compliance
- Provides clear guidelines for users

### **Better User Experience:**
- Clear content policies
- Appropriate model selection
- Transparent filtering system

### **Compliance:**
- Meets platform safety requirements
- Prevents harmful content
- Maintains appropriate boundaries

## 🔧 **Configuration**

### **Customizing Filtering:**
Edit `content_filter.py` to modify:
- Drug keywords list
- Violence keywords list
- Harassment keywords list
- NSFW indicators
- Model-specific rules

### **Adding New Models:**
1. Add model ID to filtering logic
2. Define model-specific guidelines
3. Test with content filter test suite

## 🐛 **Troubleshooting**

### **Common Issues:**

1. **Content not being filtered:**
   - Check if content filter is imported
   - Verify model ID matches exactly
   - Check NSFW mode status

2. **False positives:**
   - Review keyword lists in `content_filter.py`
   - Add exceptions for legitimate content
   - Test with specific cases

3. **Model not responding:**
   - Check model status with `/status`
   - Verify API keys are configured
   - Check subscription limits

### **Debug Commands:**
- `/status` - Check bot and model status
- `/contentfilter` - View filtering information
- `/modelinfo <model>` - Check model guidelines

## 📝 **Future Enhancements**

### **Planned Features:**
- **Custom keyword lists** per server
- **User-specific filtering** preferences
- **Advanced ML-based** content detection
- **Real-time filtering** statistics
- **Admin moderation** tools

### **Integration Opportunities:**
- **Database logging** of filtered content
- **User reporting** system
- **Automated moderation** actions
- **Content analytics** dashboard

## 🎉 **Summary**

The content filtering system successfully allows the Dolphin Mistral model to handle NSFW content while maintaining strict boundaries against drug-related topics. This provides users with appropriate adult conversation capabilities while ensuring platform safety and compliance.

**Key Achievements:**
- ✅ Dolphin model allows NSFW content in NSFW mode
- ❌ Dolphin model blocks all drug-related content
- 🛡️ All models block violence and harassment
- 📋 Clear guidelines and user education
- 🧪 Comprehensive testing system
- 🔧 Easy configuration and maintenance

