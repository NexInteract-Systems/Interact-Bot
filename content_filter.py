"""
Content Filter for AI Discord Bot
Handles content filtering for different models, especially NSFW vs drug-related content
"""

import re
from typing import List, Dict, Tuple, Optional
from enum import Enum

class ContentType(Enum):
    """Types of content that can be filtered"""
    SFW = "sfw"
    NSFW = "nsfw"
    DRUGS = "drugs"
    VIOLENCE = "violence"
    HARASSMENT = "harassment"

class ContentFilter:
    """Content filtering system for different AI models"""
    
    def __init__(self):
        # Drug-related keywords and phrases to block
        self.drug_keywords = [
            # Common drug names
            'cocaine', 'crack', 'heroin', 'methamphetamine', 'meth', 'ecstasy', 'mdma',
            'lsd', 'acid', 'mushrooms', 'psilocybin', 'marijuana', 'cannabis', 'weed',
            'hash', 'opium', 'morphine', 'fentanyl', 'oxycodone', 'vicodin', 'percocet',
            'xanax', 'valium', 'adderall', 'ritalin', 'ketamine', 'ghb', 'rohypnol',
            'bath salts', 'spice', 'k2', 'synthetic marijuana', 'dmt', 'ayahuasca',
            
            # Drug-related terms
            'drug dealer', 'drug dealing', 'drug trafficking', 'drug smuggling',
            'drug abuse', 'drug addiction', 'drug dependency', 'drug overdose',
            'drug paraphernalia', 'drug testing', 'drug rehab', 'drug treatment',
            'injecting', 'snorting', 'smoking drugs', 'drug use', 'getting high',
            'drug party', 'drug scene', 'drug culture', 'drug lifestyle',
            'drug war', 'drug policy', 'drug laws', 'drug enforcement',
            
            # Slang terms
            'dope', 'crackhead', 'junkie', 'addict', 'stoner', 'pothead',
            'tweaker', 'crack pipe', 'needle', 'syringe', 'bong', 'pipe',
            'rolling papers', 'grinder', 'scale', 'baggie', 'dime bag',
            'high on', 'get high', 'getting high', 'being high',
            
            # Manufacturing terms
            'cooking meth', 'meth lab', 'drug lab', 'drug manufacturing',
            'drug production', 'drug synthesis', 'drug extraction',
            
            # Distribution terms
            'drug market', 'drug trade', 'drug business', 'drug money',
            'drug profits', 'drug cartel', 'drug gang', 'drug organization'
        ]
        
        # Violence-related keywords (optional - can be enabled/disabled)
        self.violence_keywords = [
            'murder', 'kill', 'killing', 'homicide',
            'torture', 'torturing', 'mutilation', 'dismemberment',
            'suicide', 'self-harm', 'cutting', 'burning', 'poisoning',
            'bomb', 'bombing', 'explosive', 'weapon', 'gun', 'knife',
            'violence', 'violent', 'brutal', 'savage', 'cruel'
        ]
        
        # Political context keywords - when these appear with violence keywords in Dolphin, allow discussion
        self.political_keywords = [
            'political', 'politics', 'politician', 'leader', 'government', 'election',
            'policy', 'debate', 'scenario', 'diplomacy', 'geopolitics', 'foreign',
            'opinion', 'analysis', 'discussion', 'theory', 'hypothesis', 'speculate',
            'modi', 'putin', 'trump', 'biden', 'xijinping', 'state', 'country',
            'summit', 'conference', 'sco', 'nato', 'un', 'g20', 'g7'
        ]
        
        # Terms that suggest discussion rather than actual threats
        self.discussion_terms = [
            'opinion', 'think', 'believe', 'discuss', 'analysis', 'view', 'perspective',
            'what if', 'scenario', 'theory', 'hypothesis', 'speculate', 'consider'
        ]
        
        # Harassment keywords (optional)
        self.harassment_keywords = [
            'doxxing', 'doxx', 'dox', 'stalking', 'stalk', 'harassment',
            'harass', 'threaten', 'threat', 'intimidate', 'intimidation',
            'bully', 'bullying', 'cyberbully', 'cyberbullying'
        ]
        
        # Compile regex patterns for better matching
        self.drug_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                             for keyword in self.drug_keywords]
        self.violence_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                 for keyword in self.violence_keywords]
        self.political_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                for keyword in self.political_keywords]
        self.discussion_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                    for keyword in self.discussion_terms]
        self.harassment_patterns = [re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE) 
                                   for keyword in self.harassment_keywords]
    
    def _is_political_context(self, text: str) -> bool:
        """Check if text is in a political context"""
        text_lower = text.lower()
        has_political_keyword = any(pattern.search(text) for pattern in self.political_patterns)
        has_discussion_term = any(pattern.search(text) for pattern in self.discussion_patterns)
        
        # Check for "assassination" in political context
        assassination_in_context = (
            re.search(r'\bassassination\b', text_lower) and 
            (has_political_keyword or has_discussion_term or 'plan' in text_lower)
        )
        
        return has_political_keyword or assassination_in_context

    def detect_content_type(self, text: str) -> List[ContentType]:
        """Detect what types of content are present in the text"""
        detected_types = []
        text_lower = text.lower()
        
        # Check for drug-related content
        if any(pattern.search(text) for pattern in self.drug_patterns):
            detected_types.append(ContentType.DRUGS)
        
        # Check for violence-related content (excluding assassination for political context check)
        has_assassination = 'assassination' in text_lower or 'assassinat' in text_lower
        has_other_violence = any(pattern.search(text) for pattern in self.violence_patterns)
        
        # Only flag violence if it's not in a political context
        if has_other_violence or (has_assassination and not self._is_political_context(text)):
            detected_types.append(ContentType.VIOLENCE)
        
        # Check for harassment-related content
        if any(pattern.search(text) for pattern in self.harassment_patterns):
            detected_types.append(ContentType.HARASSMENT)
        
        # Determine if content is NSFW (adult content but not drugs/violence)
        nsfw_indicators = [
            # Sexual terms
            'sex', 'sexual', 'intercourse', 'sexuality', 'sexuality', 'sexual activity',
            'porn', 'pornography', 'erotic', 'erotica', 'horny', 'sexy',
            # Body parts
            'nude', 'naked', 'bare', 'topless', 'bottomless', 'exposed',
            'breast', 'boobs', 'tits', 'nipples', 'ass', 'butt', 'booty',
            'penis', 'cock', 'dick', 'dildo', 'phallus', 'erection',
            'vagina', 'pussy', 'clit', 'clitoris', 'labia', 'vulva',
            'anus', 'butthole', 'asshole', 'rimming',
            # Sexual acts
            'orgasm', 'cum', 'ejaculate', 'cumming', 'climax', 'orgasmic',
            'masturbation', 'masturbate', 'jerking off', 'wanking',
            'oral sex', 'blowjob', 'fellatio', 'cunnilingus', 'rimjob',
            'anal', 'anal sex', 'fucking', 'fuck', 'thrust', 'thrusting',
            'foreplay', 'petting', 'groping', 'fondling', 'touching',
            # BDSM and fetishes
            'bdsm', 'domination', 'submission', 'sadism', 'masochism',
            'fetish', 'fetishes', 'kink', 'kinky', 'rough', 'dominant', 'submissive',
            'spanking', 'whipping', 'bondage', 'restraint', 'choking',
            # Intimate/romantic terms
            'intimate', 'intimacy', 'lovemaking', 'making love', 'romantic',
            'love', 'relationship', 'dating', 'flirting', 'seduction',
            'passion', 'passionate', 'desire', 'lust', 'lustful', 'lusty',
            'arousal', 'aroused', 'turned on', 'horny', 'turned off',
            'foreplay', 'afterplay', 'foreplay',
            # Adult activities
            'stripper', 'stripping', 'lap dance', 'strip club',
            'escort', 'escort service', 'prostitute', 'prostitution',
            'orgy', 'threesome', 'group sex', 'gangbang',
            # Adult media/content
            'adult', 'adult content', 'adult film', 'xxx', 'nudes',
            'naked pictures', 'nude photos', 'sexy pics', 'sexy photos'
        ]
        
        nsfw_patterns = [re.compile(r'\b' + re.escape(indicator) + r'\b', re.IGNORECASE) 
                        for indicator in nsfw_indicators]
        
        if any(pattern.search(text) for pattern in nsfw_patterns):
            # Only mark as NSFW if it's not drug-related
            if ContentType.DRUGS not in detected_types:
                detected_types.append(ContentType.NSFW)
        
        # If no specific content types detected, assume SFW
        if not detected_types:
            detected_types.append(ContentType.SFW)
        
        return detected_types
    
    def should_block_content(self, text: str, model_id: str, is_nsfw_mode: bool) -> Tuple[bool, str]:
        """
        Determine if content should be blocked based on model and mode
        
        Returns:
            Tuple of (should_block, reason)
        """
        detected_types = self.detect_content_type(text)
        
        # Special handling for violence in political/political discussion contexts
        is_political = self._is_political_context(text)
        
        # Special handling for Dolphin model - allow political discussions and full NSFW content
        if model_id == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free":
            # In NSFW mode for Dolphin: Allow ALL content except drugs and harassment
            if is_nsfw_mode:
                # Block only drugs and harassment, allow EVERYTHING else (NSFW, violence, etc.)
                if ContentType.DRUGS in detected_types:
                    return True, "Drug-related content is not allowed on this platform."
                if ContentType.HARASSMENT in detected_types:
                    return True, "Harassment content is not allowed on this platform."
                # Allow ALL other content including explicit sexual content, violence, etc.
                return False, ""
            
            # In SFW mode for Dolphin: Allow political discussions
            elif is_political:
                # Allow political discussions, but block drugs, harassment, and NSFW
                if ContentType.DRUGS in detected_types:
                    return True, "Drug-related content is not allowed on this platform."
                if ContentType.HARASSMENT in detected_types:
                    return True, "Harassment content is not allowed on this platform."
                if ContentType.NSFW in detected_types:
                    return True, "NSFW content is only allowed in NSFW mode. Use `!togglemode` to enable NSFW mode."
                return False, ""
            
            # In SFW mode, block NSFW, drugs, harassment, and non-political violence
            elif ContentType.DRUGS in detected_types:
                return True, "Drug-related content is not allowed on this platform."
            elif ContentType.NSFW in detected_types:
                return True, "NSFW content is only allowed in NSFW mode. Use `!togglemode` to enable NSFW mode."
            elif ContentType.VIOLENCE in detected_types:
                return True, "Violent content is not allowed on this platform."
            elif ContentType.HARASSMENT in detected_types:
                return True, "Harassment content is not allowed on this platform."
        else:
            # For other models, block drugs and harassment always
            if ContentType.DRUGS in detected_types:
                return True, "Drug-related content is not allowed on this platform."
            if ContentType.HARASSMENT in detected_types:
                return True, "Harassment content is not allowed on this platform."
            
            # For other models, block violence unless it's clearly political
            if ContentType.VIOLENCE in detected_types and not is_political:
                return True, "Violent content is not allowed on this platform."
            
            # For other models, apply standard filtering
            if not is_nsfw_mode and ContentType.NSFW in detected_types:
                return True, "NSFW content is only allowed in NSFW mode. Use `!togglemode` to enable NSFW mode."
        
        return False, ""  # Allow content
    
    def get_content_warning(self, text: str, model_id: str) -> Optional[str]:
        """Get a content warning message if needed"""
        detected_types = self.detect_content_type(text)
        
        if ContentType.NSFW in detected_types and model_id == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free":
            return "⚠️ This conversation may contain adult content. Please ensure you're in an appropriate channel."
        
        return None
    
    def filter_response(self, response: str, model_id: str, is_nsfw_mode: bool) -> str:
        """
        Filter AI response to remove inappropriate content
        """
        # For Dolphin in NSFW mode, pass through ALL content (except drugs/harassment)
        if model_id == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free" and is_nsfw_mode:
            # Only block drugs and harassment, allow everything else
            detected_types = self.detect_content_type(response)
            if ContentType.DRUGS in detected_types:
                return f"❌ I cannot provide that response: Drug-related content is not allowed on this platform."
            if ContentType.HARASSMENT in detected_types:
                return f"❌ I cannot provide that response: Harassment content is not allowed on this platform."
            # Allow ALL other content without filtering
            return response
        
        # For other cases, check if response should be blocked
        should_block, reason = self.should_block_content(response, model_id, is_nsfw_mode)
        
        if should_block:
            return f"❌ I cannot provide that response: {reason}"
        
        return response
    
    def get_model_guidelines(self, model_id: str) -> str:
        """Get content guidelines for a specific model"""
        if model_id == "cognitivecomputations/dolphin-mistral-24b-venice-edition:free":
            return (
                "🔞 **Dolphin Mistral 24B - Content Guidelines:**\n"
                "✅ **Allowed in NSFW mode:** Adult content, sexual topics, romantic discussions\n"
                "✅ **Political discussions:** Political opinions and geopolitical analysis (including violent scenarios in political context)\n"
                "❌ **Never allowed:** Drug-related content, harassment\n"
                "⚠️ **Note:** This model is designed for adult conversations and political discourse while maintaining strict boundaries against harmful content."
            )
        else:
            return (
                "🛡️ **Standard Content Guidelines:**\n"
                "✅ **Allowed:** Safe-for-work content, general discussions, political opinions\n"
                "❌ **Not allowed:** NSFW content, drugs, non-political violence, harassment\n"
                "💡 **Tip:** Use `!togglemode` to enable NSFW mode for adult content."
            )

# Global content filter instance
content_filter = ContentFilter()
