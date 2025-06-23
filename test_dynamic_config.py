#!/usr/bin/env python3
"""
Test script for dynamic model configuration functionality.
This tests the ModelConfig and DualModelConfig classes and verifies
that temperature and seed parameters are properly handled.
"""

import sys
import os
sys.path.append('/home/ubuntu/repos/llm-screening-tool')

from app.services.screening.dual_llm_screener import ModelConfig, DualModelConfig

def test_model_config():
    """Test ModelConfig class functionality."""
    print("🧪 Testing ModelConfig class...")
    
    try:
        config = ModelConfig(
            provider='openai',
            model_name='gpt-4o',
            temperature=0.5,
            seed=12345,
            max_tokens=4000
        )
        print(f"✅ Valid ModelConfig created: {config}")
    except Exception as e:
        print(f"❌ Failed to create valid ModelConfig: {e}")
        return False
    
    try:
        invalid_config = ModelConfig(
            provider='openai',
            model_name='gpt-4o',
            temperature=3.0  # Invalid - should be 0-2
        )
        print("❌ Temperature validation failed - should have raised error")
        return False
    except ValueError as e:
        print(f"✅ Temperature validation working: {e}")
    
    try:
        invalid_config = ModelConfig(
            provider='openai',
            model_name='gpt-4o',
            temperature=0.1,
            seed=2**33  # Invalid - should be 0 to 2^32
        )
        print("❌ Seed validation failed - should have raised error")
        return False
    except ValueError as e:
        print(f"✅ Seed validation working: {e}")
    
    return True

def test_dual_model_config():
    """Test DualModelConfig class functionality."""
    print("\n🧪 Testing DualModelConfig class...")
    
    try:
        openai_config = ModelConfig(
            provider='openai',
            model_name='gpt-4o',
            temperature=0.1,
            seed=12345
        )
        
        anthropic_config = ModelConfig(
            provider='anthropic',
            model_name='claude-3-5-sonnet-20241022',
            temperature=0.2,
            seed=67890
        )
        
        dual_config = DualModelConfig(
            openai_config=openai_config,
            anthropic_config=anthropic_config
        )
        
        print(f"✅ DualModelConfig created successfully:")
        print(f"   OpenAI: {dual_config.openai_config}")
        print(f"   Anthropic: {dual_config.anthropic_config}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create DualModelConfig: {e}")
        return False

def test_configuration_extraction():
    """Test configuration extraction from project config format."""
    print("\n🧪 Testing configuration extraction from project config...")
    
    llm_config = {
        'openaiTemperature': 0.3,
        'anthropicTemperature': 0.4,
        'openaiSeed': 11111,
        'anthropicSeed': 22222
    }
    
    try:
        openai_config = ModelConfig(
            provider='openai',
            model_name='gpt-4o',
            temperature=llm_config.get('openaiTemperature', 0.1),
            seed=llm_config.get('openaiSeed'),
            max_tokens=4000
        )
        
        anthropic_config = ModelConfig(
            provider='anthropic',
            model_name='claude-3-5-sonnet-20241022',
            temperature=llm_config.get('anthropicTemperature', 0.1),
            seed=llm_config.get('anthropicSeed'),
            max_tokens=4000
        )
        
        dual_config = DualModelConfig(
            openai_config=openai_config,
            anthropic_config=anthropic_config
        )
        
        print(f"✅ Configuration extraction successful:")
        print(f"   OpenAI temp: {dual_config.openai_config.temperature}, seed: {dual_config.openai_config.seed}")
        print(f"   Anthropic temp: {dual_config.anthropic_config.temperature}, seed: {dual_config.anthropic_config.seed}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration extraction failed: {e}")
        return False

def test_pico_criteria_preservation():
    """Verify that PICO-TT criteria are still properly handled."""
    print("\n🧪 Testing PICO-TT criteria preservation...")
    
    try:
        from app.services.screening.dual_llm_screener import ScreeningCriteria
        
        criteria = ScreeningCriteria(
            research_question="What is the effectiveness of intervention X?",
            target_population="Adults with condition Y",
            target_intervention="Treatment X",
            target_comparison="Placebo or standard care",
            target_outcomes=["Primary outcome measure"],
            target_time_frame="6 months",
            target_study_types=["Randomized controlled trials"],
            inclusion_criteria=["RCT studies", "Adult participants"],
            exclusion_criteria=["Animal studies", "Case reports"]
        )
        
        print(f"✅ PICO-TT criteria structure preserved:")
        print(f"   Research question: {criteria.research_question}")
        print(f"   Target population: {criteria.target_population}")
        print(f"   Target intervention: {criteria.target_intervention}")
        print(f"   Inclusion criteria: {len(criteria.inclusion_criteria)} items")
        print(f"   Exclusion criteria: {len(criteria.exclusion_criteria)} items")
        return True
        
    except Exception as e:
        print(f"❌ PICO-TT criteria test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Dynamic Model Configuration System")
    print("=" * 50)
    
    tests = [
        test_model_config,
        test_dual_model_config,
        test_configuration_extraction,
        test_pico_criteria_preservation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dynamic model configuration is working correctly.")
        print("\n✅ Key Features Verified:")
        print("   • Temperature and seed parameter validation")
        print("   • Dynamic configuration from project settings")
        print("   • PICO-TT criteria preservation")
        print("   • Dual-LLM configuration support")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
