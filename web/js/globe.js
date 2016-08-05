var $ = require("jquery");
var THREE = require("THREE");

const R = 637.8;
const MINUTES_PER_DAY = 5;

function toRadians(d) {
	return d * Math.PI / 180.0;
}

class EarthScene {
	constructor() {
		this.container = document.getElementById( 'scene-container' );
		this.camera = new THREE.PerspectiveCamera( 36, window.innerWidth / window.innerHeight, 1, 100000000 );
		this.camera.position.z = 3000;
		this.camera.lookAt(0, 0, 0);
		this.scene = new THREE.Scene();

		this.raycaster = new THREE.Raycaster();
		this.mouse = new THREE.Vector2();

		this.ambientLight = new THREE.AmbientLight( 0x444444 );
		this.scene.add( this.ambientLight );

		this.lights = [];
		this.lights[ 0 ] = new THREE.PointLight( 0xffffff, .6, 0 );
		this.lights[ 0 ].position.set( -700, 0, 1000 );
		this.scene.add( this.lights[ 0 ] );

		this.renderer = new THREE.WebGLRenderer( { antialias: false } );
		this.renderer.setPixelRatio( window.devicePixelRatio );
		this.renderer.setSize( window.innerWidth, window.innerHeight );
		this.container.appendChild( this.renderer.domElement );

		var onWindowResize = function() {
			this.camera.aspect = window.innerWidth / window.innerHeight;
			this.camera.updateProjectionMatrix();
			renderer.setSize( window.innerWidth, window.innerHeight );
		}
		window.addEventListener( 'resize', onWindowResize, false );

		// this.controls = new THREE.OrbitControls( this.camera, this.renderer.domElement );
		// this.controls.enableDamping = true;
		// this.controls.dampingFactor = 0.25;
		// this.controls.enableZoom = true;

		// var onDocumentMouseDown = function( event ) {
		// 	event.preventDefault();
		// 	this.mouse.x = ( event.clientX / this.renderer.domElement.clientWidth ) * 2 - 1;
		// 	this.mouse.y = - ( event.clientY / this.renderer.domElement.clientHeight ) * 2 + 1;
		// 	this.raycaster.setFromCamera( this.mouse, this.camera );

		// 	var intersects = this.raycaster.intersectObjects( [globeMesh] );
		// 	if ( intersects.length > 0 ) {
		// 		console.log(geo_data[intersects[0].face.grid_index]);
		// 	}
		// }
		// document.addEventListener( 'mousedown', onDocumentMouseDown, false );

		this.start = Date.now();
		this.last = Date.now();
		this.globe = new Globe(this);
		this.animate();
	}

	animate() {
		requestAnimationFrame( this.animate );
		this.renderer.render( this.scene, this.camera );

		var now = Date.now();
		var elapsed = now - this.last;
		var deltaTheta = 2 * Math.PI * (elapsed / (MINUTES_PER_DAY * 60000));
		this.globeMesh.rotation.y += deltaTheta;
		// $.each(variableMeshes, function(i, mesh) { mesh.rotation.y += deltaTheta });
		this.last = now;

		elapsed = this.now - this.start;
		// moonMesh.position.set(
		// 	38400 * Math.cos(2 * Math.PI * (elapsed / (MINUTES_PER_DAY * 30 * 60000))),
		// 	0,
		// 	38400 * Math.sin(-2 * Math.PI * (elapsed / (MINUTES_PER_DAY * 30 * 60000)))
		// 	);
	}
}

class Globe {
	constructor(earthScene) {
		this.earthScene = earthScene
		this.geo = new THREE.Geometry();
		var vi = 0;
		$.each(json, function(i) {
			var cell = json[i];
			createCellGeometry(geo, cell, R, vi);
			vi = vi + 12;
		});
		geo.computeBoundingSphere();
		geo.computeFaceNormals();
		geo.computeVertexNormals();
		var material = new THREE.MeshPhongMaterial( 
			{
				wireframe: false, 
				color: 0xffffff, 
				emissive: 0x111122,
				shading: THREE.FlatShading,
				vertexColors: THREE.FaceColors,
				side: THREE.DoubleSide
			} 
		);
		this.globeMesh = new THREE.Mesh(geo, material);
		this.earthScene.scene.add(globeMesh);
	}

	/* Convert the vertex locations in lat/lon and radius to Cartesian coordinates
	 */
	getVertexPositions(cellData, R) {
		return $.map(cellData.vertices, function(v) {
			return [[-1 * R * Math.cos(toRadians(v[1])) * Math.cos(toRadians(v[0])),
							 1 * R * Math.sin(toRadians(v[1])),
							 1 * R * Math.cos(toRadians(v[1])) * Math.sin(toRadians(v[0]))
							 ]]
		})
	}

	static createCellGeometry(geo, cell, R, vi) {
		var dR;
		if (cell.atts.hasOwnProperty('STD_ELEV')) 
			dR = R * (.00001 * cell.atts.STD_ELEV);
		else
			dR = 0;
		var vp1 = getVertexPositions(cell, R + dR);
		var vp2 = getVertexPositions(cell, R - dR);
		geo.vertices.push(
			new THREE.Vector3(vp1[0][0], vp1[0][1], vp1[0][2]),
			new THREE.Vector3(vp1[1][0], vp1[1][1], vp1[1][2]),
			new THREE.Vector3(vp1[2][0], vp1[2][1], vp1[2][2]),
			new THREE.Vector3(vp1[3][0], vp1[3][1], vp1[3][2]),
			new THREE.Vector3(vp1[4][0], vp1[4][1], vp1[4][2]),
			new THREE.Vector3(vp1[5][0], vp1[5][1], vp1[5][2]),
			new THREE.Vector3(vp2[0][0], vp2[0][1], vp2[0][2]),
			new THREE.Vector3(vp2[1][0], vp2[1][1], vp2[1][2]),
			new THREE.Vector3(vp2[2][0], vp2[2][1], vp2[2][2]),
			new THREE.Vector3(vp2[3][0], vp2[3][1], vp2[3][2]),
			new THREE.Vector3(vp2[4][0], vp2[4][1], vp2[4][2]),
			new THREE.Vector3(vp2[5][0], vp2[5][1], vp2[5][2])
		);
		faces = [
			// outer tile
			new THREE.Face3(0+vi, 1+vi, 2+vi),
			new THREE.Face3(3+vi, 4+vi, 5+vi),
			new THREE.Face3(0+vi, 2+vi, 3+vi),
			new THREE.Face3(0+vi, 3+vi, 5+vi),
			// walls
			new THREE.Face3( 0+vi, 6+vi, 7+vi),
			new THREE.Face3( 7+vi, 1+vi, 0+vi),
			new THREE.Face3( 1+vi, 7+vi, 8+vi),
			new THREE.Face3( 8+vi, 2+vi, 1+vi),
			new THREE.Face3( 2+vi, 8+vi, 9+vi),
			new THREE.Face3( 9+vi, 3+vi, 2+vi),
			new THREE.Face3( 3+vi, 9+vi,10+vi),
			new THREE.Face3(10+vi, 4+vi, 3+vi),
			new THREE.Face3( 4+vi,10+vi,11+vi),
			new THREE.Face3(11+vi, 5+vi, 4+vi),
			new THREE.Face3( 5+vi,11+vi, 6+vi),
			new THREE.Face3( 6+vi, 0+vi, 5+vi)

			// inner tile
		];
		$.each(faces, function(i, f) { f.grid_index = cell.grid_index })
		// faces = [
		// 	new THREE.Face3(2+vi, 1+vi, 0+vi),
		// 	new THREE.Face3(5+vi, 4+vi, 3+vi),
		// 	new THREE.Face3(3+vi, 2+vi, 0+vi),
		// 	new THREE.Face3(5+vi, 3+vi, 0+vi)
		// ];

		if (false && cell.atts.PCT_URBAN > 2.5)
			$.each(faces, function(i, face) { face.color.setRGB( .6, .6, .2); });
		else if (cell.hasOwnProperty('location_name') && cell.location_name != null)
			$.each(faces, function(i, face) { face.color.setRGB( .2, .2, .2); });
		else if (cell.atts.PCT_LAKE > 5)
			$.each(faces, function(i, face) { face.color.setRGB( 0, .4, .6); });
		else if (cell.atts.PCT_GLACIER > 5)
			$.each(faces, function(i, face) { face.color.setRGB( .8, .8, .9); });
		// else if (cell.atts.SOIL_COLOR < 10)
		// 	$.each(faces, function(i, face) { face.color.setRGB( .85, .75, .5); });
		else if ((cell.atts.LANDFRAC_PFT > .5 && cell.atts.STD_ELEV > 1)
			       || cell.atts.LANDFRAC_PFT > .6)
			$.each(faces, function(i, face) { face.color.setRGB( .2, .35, .2); });
		else
			$.each(faces, function(i, face) { face.color.setRGB( .1, .1, .8); });
		
		$.each(faces, function(i, face) { geo.faces.push(face); });
		return;
	}

	displayVariable(data, height, min, max) {
		var Rv = R * height;
		var geo = new THREE.Geometry();
		var vi = 0;
		$.each(this.geo_data, function(i, cell) {
			var vp = getVertexPositions(cell, Rv);
			geo.vertices.push(
				new THREE.Vector3(vp[0][0], vp[0][1], vp[0][2]),
				new THREE.Vector3(vp[1][0], vp[1][1], vp[1][2]),
				new THREE.Vector3(vp[2][0], vp[2][1], vp[2][2]),
				new THREE.Vector3(vp[3][0], vp[3][1], vp[3][2]),
				new THREE.Vector3(vp[4][0], vp[4][1], vp[4][2]),
				new THREE.Vector3(vp[5][0], vp[5][1], vp[5][2]));
			var faces = [
				// outer tile
				new THREE.Face3(0+vi, 1+vi, 2+vi),
				new THREE.Face3(3+vi, 4+vi, 5+vi),
				new THREE.Face3(0+vi, 2+vi, 3+vi),
				new THREE.Face3(0+vi, 3+vi, 5+vi),
			];
			vi += 6;
			var range = max - min;
			var v = Math.min(Math.max(data[cell.grid_index] - min, 0), range) / range;
			$.each(faces, function(i, face) { face.color.setHSL( v, 1.0, 0.5 ); });
			$.each(faces, function(i, face) { geo.faces.push(face); });
		});

		geo.computeBoundingSphere();
		geo.computeFaceNormals();
		geo.computeVertexNormals();
		var material = new THREE.MeshPhongMaterial( 
			{
				color: 0xffffff,
				shading: THREE.FlatShading,
				vertexColors: THREE.FaceColors,
				transparent: true,
				opacity: 0.35
			} 
		);
		var variableMesh = new THREE.Mesh(geo, material);
		this.earthScene.scene.add(variableMesh);
		variableMesh.rotation.y = globeMesh.rotation.y;
		// variableMeshes.push(variableMesh);
	}
}

// class Sun extends THREE.Mesh {
// 	constructor() {

// 	}
// }

// class Moon extends THREE.Mesh {

// }

module.exports = {
	EarthScene: EarthScene
}