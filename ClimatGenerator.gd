class_name ClimateGenerator
extends RefCounted

static func build_profile(
coord:Vector2i
)->ClimateProfile:

	var p:=ClimateProfile.new()

	var pos=Vector2(coord)*160

	var continent=WorldSeed.continent(pos)

	var height=WorldSeed.height(pos)

	var moisture=WorldSeed.moisture(pos)

	var climate=WorldSeed.climate(pos)

	height+=continent*0.8

	p.average_height=height

	p.average_moisture=moisture

	p.latitude=pos.y/120000.0

	p.average_temperature=

		climate

		-p.latitude

		-height*0.45

	p.wind_strength=

		0.5

		+abs(p.latitude)

	p.wind_direction=

		Vector2.RIGHT.rotated(

			p.latitude

		)

	p.rainfall=

		clamp(

			moisture*0.7

			+continent*0.3,

			0,

			1

		)

	p.tectonic_activity=

		max(

			0,

			height

		)

	return p