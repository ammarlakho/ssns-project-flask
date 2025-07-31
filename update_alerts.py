#!/usr/bin/env python3
"""
One-time script to update existing parameters with proper default alert configurations
Run this script once to upgrade your database with better alert messages.
"""

from database import db

def update_alert_defaults():
    """Update existing parameters with proper default alert configurations"""
    print("🔄 Updating Alert Configurations...")
    print("=" * 50)
    
    # Define the proper default alert configurations
    alert_defaults = {
        'co2': {
            'alert_type': 'ventilation_required',
            'warning_title': '🪟 Ventilation Recommended',
            'warning_message': 'CO2 levels are elevated ({value} ppm). Consider opening windows for better air circulation.',
            'danger_title': '🚨 Immediate Ventilation Required',
            'danger_message': 'CO2 levels are dangerously high ({value} ppm). Open windows immediately and increase ventilation.'
        },
        'vocs': {
            'alert_type': 'ventilation_required',
            'warning_title': '🪟 VOC Levels Elevated',
            'warning_message': 'VOC levels are elevated ({value} ppb). Consider improving ventilation.',
            'danger_title': '🚨 High VOC Levels Detected',
            'danger_message': 'VOC levels are dangerously high ({value} ppb). Increase ventilation and check for sources.'
        },
        'pm25': {
            'alert_type': 'air_quality',
            'warning_title': '⚠️ Moderate Air Quality - PM2.5',
            'warning_message': 'PM2.5 levels are elevated ({value} μg/m³). Monitor air quality.',
            'danger_title': '🚨 Poor Air Quality - PM2.5',
            'danger_message': 'PM2.5 levels are dangerously high ({value} μg/m³). Improve air filtration and ventilation.'
        },
        'pm10': {
            'alert_type': 'air_quality',
            'warning_title': '⚠️ Moderate Air Quality - PM10',
            'warning_message': 'PM10 levels are elevated ({value} μg/m³). Monitor air quality.',
            'danger_title': '🚨 Poor Air Quality - PM10',
            'danger_message': 'PM10 levels are dangerously high ({value} μg/m³). Improve air filtration and ventilation.'
        },
        'temperature': {
            'alert_type': 'comfort',
            'warning_title': '🌡️ Temperature Alert',
            'warning_message': 'Temperature is outside optimal range ({value}°C). Consider adjusting settings.',
            'danger_title': '🌡️ Extreme Temperature',
            'danger_message': 'Temperature is outside comfortable range ({value}°C). Adjust HVAC settings.'
        },
        'humidity': {
            'alert_type': 'comfort',
            'warning_title': '💧 Humidity Alert',
            'warning_message': 'Humidity is outside optimal range ({value}%). Consider adjusting settings.',
            'danger_title': '💧 Extreme Humidity',
            'danger_message': 'Humidity is outside comfortable range ({value}%). Adjust humidity control.'
        }
    }
    
    try:
        # Initialize database connection
        db.initialize_database()
        print("✅ Database connection established")
        
        # Get current parameters
        current_params = db.get_all_parameters()
        print(f"📊 Found {len(current_params)} existing parameters")
        
        updated_count = 0
        
        # Update each parameter with proper alert defaults
        for param_name, alert_config in alert_defaults.items():
            if param_name in current_params:
                print(f"\n🔧 Updating {param_name}...")
                
                # Show current alert titles
                current = current_params[param_name]
                print(f"   Current Warning: {current.get('warning_title', 'N/A')}")
                print(f"   Current Danger:  {current.get('danger_title', 'N/A')}")
                
                # Update with new alert configuration
                success = db.update_parameter(param_name, alert_config)
                
                if success:
                    print(f"   ✅ Updated {param_name} alert configuration")
                    updated_count += 1
                else:
                    print(f"   ❌ Failed to update {param_name}")
            else:
                print(f"\n⚠️  Parameter {param_name} not found in database")
        
        print(f"\n🎉 Update Complete!")
        print(f"   Updated {updated_count} parameters")
        
        # Show updated configurations
        print(f"\n📋 Updated Alert Configurations:")
        updated_params = db.get_all_parameters()
        for param_name in alert_defaults.keys():
            if param_name in updated_params:
                param = updated_params[param_name]
                print(f"\n   {param['name']} ({param_name}):")
                print(f"     Type: {param.get('alert_type', 'N/A')}")
                print(f"     Warning: {param.get('warning_title', 'N/A')}")
                print(f"     Danger: {param.get('danger_title', 'N/A')}")
        
        print(f"\n✨ Your alert system is now fully configured!")
        print(f"   You can further customize alerts at /admin/parameters")
        
    except Exception as e:
        print(f"❌ Error updating alert defaults: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 Alert Configuration Update Script")
    print("This will update your existing parameters with better default alert messages.")
    
    response = input("\nDo you want to proceed? (y/N): ").lower().strip()
    
    if response in ['y', 'yes']:
        update_alert_defaults()
    else:
        print("❌ Update cancelled")