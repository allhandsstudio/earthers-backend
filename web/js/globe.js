var $ = require("jquery");
var THREE = require("THREE");
var TWEEN = require("tween.js");
var utils = require("./utils.js");
THREE.OrbitControls = require("./OrbitControls.js").OrbitControls;

const PROVIDER_URI = 'https://4vesdtyv82.execute-api.us-west-2.amazonaws.com/dev';

const R = 637.8;
const MINUTES_PER_DAY = 5;
const FRAMES_PER_MONTH = 20;

function toRadians(d) {
	return d * Math.PI / 180.0;
}

var container, camera, scene, raycaster, mouse, ambientLight, lights, renderer, controls;
var globe;
var shells = [];
var start, last;
var data1 = null, data2 = null;
var frames = []
var animationReady = false;
var frameIndex = 0;
var geo_data;

var initScene = function(data) {
	container = document.getElementById( 'scene-container' );
	camera = new THREE.PerspectiveCamera( 36, window.innerWidth / window.innerHeight, 1, 100000000 );
	camera.position.z = 3000;
	camera.lookAt(0, 0, 0);
	scene = new THREE.Scene();

	raycaster = new THREE.Raycaster();
	mouse = new THREE.Vector2();

	ambientLight = new THREE.AmbientLight( 0x888888 );
	scene.add( ambientLight );

	lights = [];
	lights[ 0 ] = new THREE.PointLight( 0xffffff, .6, 0 );
	lights[ 0 ].position.set( -700, 0, 1000 );
	scene.add( lights[ 0 ] );

	renderer = new THREE.WebGLRenderer( { antialias: true } );
	renderer.setPixelRatio( window.devicePixelRatio );
	renderer.setSize( window.innerWidth, window.innerHeight );
	container.appendChild( renderer.domElement );

	var onWindowResize = function() {
		camera.aspect = window.innerWidth / window.innerHeight;
		camera.updateProjectionMatrix();
		renderer.setSize( window.innerWidth, window.innerHeight );
	}
	window.addEventListener( 'resize', onWindowResize, false );

	controls = new THREE.OrbitControls( camera, renderer.domElement );
	controls.enableDamping = true;
	controls.dampingFactor = 0.25;
	controls.enableZoom = true;

	start = Date.now();
	last = Date.now();
	globe = new Globe(data);
	geo_data = data;
	globe.doEntranceAnimation()
	animate();
}

var animate = function() {
	requestAnimationFrame( animate );
	renderer.render( scene, camera );

	var now = Date.now();
	var elapsed = now - last;
	var deltaTheta = 2 * Math.PI * (elapsed / (MINUTES_PER_DAY * 60000));
	globe.globeMesh.rotation.y += deltaTheta;
	last = now;
	elapsed = now - start;

	TWEEN.update();

	if (shells.length > 0) {
		$.each(shells, function(i, shell) {
			shell.loadNextFrame();
			if (shell.shellCreated) shell.mesh.rotation.y += deltaTheta;
		});
	}
}

var loadVariable = function(runId, varInfo) {
	console.log(varInfo);
	if (shells.length > 0) {
		$.each(shells, (i, shell) => scene.remove(shell.mesh));
		shells = [];
	}
	var url = PROVIDER_URI+'/run/'+runId+'/variable/'+varInfo.model+'/'+varInfo.varName+'/info';
	$.ajax({
		url: url,
		dataType: 'json',
		cache: false,
		success: function(data) {
			console.log(data);
			console.log('creating shells');
			if (varInfo.type === 'flat') {
				var shell = new VariableShell(runId, varInfo.model, varInfo.varName, -1, varInfo.units);
				shell.displayVariable(varInfo.display, varInfo.color, varInfo.height);
				shells.push(shell);
			} else {
				var levs = [0, 3, 6, 9, 12];
				$.each(levs, function(i, lev) {
					var shell = new VariableShell(runId, varInfo.model, varInfo.varName, lev, varInfo.units);
					shell.displayVariable(varInfo.display, varInfo.color, varInfo.height);
					shells.push(shell);
				})
			}
		},
		error: (xhr, status, error) => {console.error(url, status, error);}
	});
};



class Globe {
	constructor(geo_data) {
		console.log('creating globe');
		var geo = new THREE.Geometry();
		var vi = 0;
		$.each(geo_data, function(i, cell) {
			Globe.createCellGeometry(geo, cell, R, vi);
			vi += 12;
		});
		geo.computeBoundingSphere();
		geo.computeFaceNormals();
		geo.computeVertexNormals();
		// geo.mergeVertices();
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
		scene.add(this.globeMesh);
		this.globeMesh.visible = false;
		this.geo_data = geo_data;
		this.geo = geo;
	}

	doEntranceAnimation() {
		var tween = new TWEEN.Tween({ r: 0 })
			.to({ r: 1 }, 2000)
			.easing(TWEEN.Easing.Cubic.InOut)
			.onUpdate(function() {globe.globeMesh.scale.set(this.r, this.r, this.r);})
			.onStart(function() {globe.globeMesh.visible = true;})
			.onComplete(() => console.log('entranceAnimation end'))
			.delay(5000)
			.start();
	}

	/* Convert the vertex locations in lat/lon and radius to Cartesian coordinates
	 */
	static getVertexPositions(cellData, R) {
		return $.map(cellData.vertices, function(v) {
			return [[-1 * R * Math.cos(toRadians(v[1])) * Math.cos(toRadians(v[0])),
							 1 * R * Math.sin(toRadians(v[1])),
							 1 * R * Math.cos(toRadians(v[1])) * Math.sin(toRadians(v[0]))
							 ]]
		})
	}

	static cellHeight(R, cell) {
		if (cell.atts.hasOwnProperty('STD_ELEV'))
			return R * (.00001 * cell.atts.STD_ELEV);
		else 
			return 0;
	}

	static createCellGeometry(geo, cell, R, vi) {
		var dR = Globe.cellHeight(R, cell);
		var vp1 = Globe.getVertexPositions(cell, R + dR);
		var vp2 = Globe.getVertexPositions(cell, R - dR);

		$.each(vp1, (i, vp) => { geo.vertices.push(new THREE.Vector3(vp[0], vp[1], vp[2]))});
		$.each(vp2, (i, vp) => { geo.vertices.push(new THREE.Vector3(vp[0], vp[1], vp[2]))});
		var faces = hexagonFaces(vi);
		faces = faces.concat([
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

			]
		);

		$.each(faces, function(i, f) { f.grid_index = cell.grid_index })

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

}

class VariableShell {
	constructor(runId, model, varName, level, units) {
		this.runId = runId;
		this.model = model;
		this.varName = varName;
		this.startTime = null;
		this.endTime = null;
		this.level = level;
		this.units = units;

		this.resetFrames();
		this.shellCreated = false;

		this.timeSteps = 24;
	}

	resetFrames() {
		this.frames = [];
		this.keyFrameInfo = [];
		this.lastFrame = -1;
		this.frameIndex = 0;		
	}

	displayVariable(displayType, displayColor, displayHeight) {
		if (displayType) this.displayType = displayType;
		if (displayColor) this.displayColor = new THREE.Color(Number(displayColor));
		if (displayHeight) this.displayHeight = displayHeight;
		else this.displayHeight = 1.02;

		console.log(displayColor);
		this.fetchInfoWithCallback(function(data) {
			var times = data.time.values;
			this.resetFrames();
			for (let i = 0; i < this.timeSteps; i++) {
				this.keyFrameInfo.push({
					time: times[i],
					frameLoaded: false,
					tweensBeforeCreated: false,
					data: null
				});
				this.fetchDataForTweens(times[i], i);
			}
		}.bind(this));
	}

	fetchDataForTweens(time, keyFrameIndex) {
		this.fetchDataWithCallback(time, this.computeVariableTweens(keyFrameIndex));
	}

	fetchInfoWithCallback(callback) {
		var url = PROVIDER_URI+'/run/'+this.runId+'/variable/'+this.model+'/'+this.varName+'/info';
		this.ajaxWithCallback(url, callback);
	}

	fetchDataWithCallback(time, callback) {
		var url = PROVIDER_URI+'/run/'+this.runId+'/variable/'+this.model+'/'+this.varName+'/data?time='+time+'&remap=C40962';
		if (this.level != -1)
			url = url+'&level='+this.level;
		this.ajaxWithCallback(url, callback);
	}

	ajaxWithCallback(url, callback) {
		// console.log('loading '+url);
		$.ajax({
			url: url,
			dataType: 'json',
			cache: false,
			success: callback,
			error: (xhr, status, error) => {console.error(url, status, error);}
		});		
	}

	computeVariableTweens(keyFrameIndex) {
		return function(varData) {
			// console.log('computeVariableTweens '+this.keyFrameInfo[keyFrameIndex]['time']);
			
			this.keyFrameInfo[keyFrameIndex].data = varData.data;
			this.keyFrameInfo[keyFrameIndex].frameLoaded = true;

			// console.log(varData);
			
			for (let i = 1; i < this.keyFrameInfo.length; i++) {
				if (!this.keyFrameInfo[i].tweensBeforeCreated 
					&& this.keyFrameInfo[i].frameLoaded && this.keyFrameInfo[i-1].frameLoaded) {
					// make the tweens!
					var data1 = this.keyFrameInfo[i-1].data;
					var data2 = this.keyFrameInfo[i].data;
					var numFrames = FRAMES_PER_MONTH;
					var delta = $.map(data1, (x, i) => {return data2[i] - data1[i]})
					var output = {};
					for (let j = 0; j < numFrames; j++) {
						var c = j / numFrames;
						var frameIndex = (i-1) * numFrames + j;
						this.frames[frameIndex] = $.map(data1, (x, k) => {return x + c * delta[k]});
					}
					this.keyFrameInfo[i].tweensBeforeCreated = true;
				}
			}
			
			if (keyFrameIndex == 0 && !this.shellCreated) {
				this.createShell(this.keyFrameInfo[keyFrameIndex].data);
				// this.createShell(this.frames[0], 1.02);
				this.shellCreated = true;
			}
		}.bind(this);
	}

	setMinMax(data) {
		var dataCopy = data.slice().sort();
		this.min = dataCopy[100];
		this.max = dataCopy[dataCopy.length - 100];
		this.range = this.max - this.min;
		console.log(this.level + ' ['+this.min+' - '+this.max+']');
	}

	getDisplayColor(value) {
		if (this.displayType == 'coverage') return this.displayColor;
		else if (this.displayType == 'increasing') return this.displayColor;
		else if (this.displayType == 'bimodal') {
			var mid = this.min + (this.max - this.min) * 0.5;
			if (value < mid) return new THREE.Color(0.0, 0.0, 1.0);
			else return new THREE.Color(1.0, 0.0, 0.0);
		}
		else return new THREE.Color(1.0, 1.0, 1.0);
	}

	getDisplayMaterial(value) {
		if (this.displayType == 'coverage' && this.units == 'frac') {
			return Math.floor(Math.max(0.0, Math.min(value, 1.0)) * 99);
		} else if (this.displayType == 'increasing' || 
			       this.displayType == 'coverage') {
			var x = Math.floor((Math.min(Math.max(value - this.min, 0), this.range) / this.range) * 75);
			if (isNaN(x))
				return 0;
			else
				return Math.min(x, 99);
		} else if (this.displayType == 'bimodal') {
			var r = this.range * 0.5;
			var mid = this.min + r;
			var x = Math.floor((Math.abs(value-mid) / r) * 60);
			if (isNaN(x))
				return 0;
			else
				return Math.min(x, 99);
		} else {
			return 0;
		}
	}

	createShell(data) {
		this.setMinMax(data);
		var geo = new THREE.Geometry();
		var vi = 0;
		geo.groups = [];
		$.each(geo_data, function(i, cell) {
			var Rv;
			if (this.displayHeight == 'ground') 
				Rv = R + Globe.cellHeight(R, cell) + .1;
			else 
				Rv = R * (this.displayHeight + this.level/1000);
			var vp1 = Globe.getVertexPositions(cell, Rv);
			$.each(vp1, (i, vp) => { geo.vertices.push(new THREE.Vector3(vp[0], vp[1], vp[2]))});
			var faces = hexagonFaces(vi);
			vi += 6;
			var v = data[cell.grid_index];
			var c = this.getDisplayColor(v);
			var m = this.getDisplayMaterial(v);
			$.each(faces, function(i, face) { 
				face.color.set(c); 
				face.materialIndex = m; 
				geo.faces.push(face);
			});
		}.bind(this));

		this.faces = geo.faces;

		geo.computeBoundingSphere();
		geo.computeFaceNormals();
		geo.computeVertexNormals();
		var bufferGeo = (new THREE.BufferGeometry()).fromGeometry(geo);
		var materials = [];
		for (let i = 0; i < 100; i++) {
			materials.push(new THREE.MeshPhongMaterial({
				color: 0xffffff,
				shading: THREE.FlatShading,
				vertexColors: THREE.FaceColors,
				transparent: true,
				opacity: (i/100)
			}));
		}
		this.mesh = new THREE.Mesh(bufferGeo, new THREE.MultiMaterial(materials));
		// var material = new THREE.MeshPhongMaterial( 
		// 	{
		// 		color: 0xffffff,
		// 		shading: THREE.FlatShading,
		// 		vertexColors: THREE.FaceColors,
		// 		transparent: true,
		// 		opacity: 0.4
		// 	} 
		// );
		// this.mesh = new THREE.Mesh(bufferGeo, material);
		scene.add(this.mesh);
		this.mesh.rotation.y = globe.globeMesh.rotation.y;
	}

	loadNextFrame() {
		for (let i = 0; i < this.frames.length; i++) {
			if (this.frames[i] != undefined) this.lastFrame = i;
			else break;
		}
		if (!this.shellCreated || this.lastFrame == -1) return;
		else {
			$.each(geo_data, function(j, cell) {
				var i = cell.grid_index;
				var v = this.frames[this.frameIndex][i]; 
				var c = this.getDisplayColor(v).getHex();
				var m = this.getDisplayMaterial(v);
				this.faces[(i*4) + 0].color.set(c);
				this.faces[(i*4) + 0].materialIndex = m;
				this.faces[(i*4) + 1].color.set(c);
				this.faces[(i*4) + 1].materialIndex = m;
				this.faces[(i*4) + 2].color.set(c);
				this.faces[(i*4) + 2].materialIndex = m;
				this.faces[(i*4) + 3].color.set(c);
				this.faces[(i*4) + 3].materialIndex = m;
			}.bind(this));
			this.computeGroups();
			// $.each(geo_data, function(j, cell) {
			// 	var i = cell.grid_index;
			// 	var v = this.frames[this.frameIndex][i]; 
			// 	var c = this.getDisplayColor(v).getHex();
			// 	var m = this.getDisplayMaterial(v);
			// 	this.mesh.geometry.faces[(i*4) + 0].color.set(c);
			// 	this.mesh.geometry.faces[(i*4) + 0].materialIndex = m;
			// 	this.mesh.geometry.faces[(i*4) + 1].color.set(c);
			// 	this.mesh.geometry.faces[(i*4) + 1].materialIndex = m;
			// 	this.mesh.geometry.faces[(i*4) + 2].color.set(c);
			// 	this.mesh.geometry.faces[(i*4) + 2].materialIndex = m;
			// 	this.mesh.geometry.faces[(i*4) + 3].color.set(c);
			// 	this.mesh.geometry.faces[(i*4) + 3].materialIndex = m;
			// }.bind(this));
			this.mesh.geometry.colorsNeedUpdate = true;
			this.mesh.geometry.groupsNeedUpdate = true;
		}
		
		this.frameIndex++;
		this.frameIndex = this.frameIndex % this.lastFrame;
	}

	computeGroups () {
		// need to do this manually because MultiMaterials seem to be broken in r79
		var group;
		var groups = [];
		var materialIndex;

		for ( var i = 0; i < this.faces.length; i ++ ) {
			var face = this.faces[ i ];

			// materials

			if ( face.materialIndex !== materialIndex ) {
				materialIndex = face.materialIndex;

				if ( group !== undefined ) {
					group.count = ( i * 3 ) - group.start;
					groups.push( group );
				}

				group = {
					start: i * 3,
					materialIndex: materialIndex
				};
			}
		}

		if ( group !== undefined ) {
			group.count = ( i * 3 ) - group.start;
			groups.push( group );
		}

		this.mesh.geometry.groups = groups;	
	}	
}

var hexagonFaces = function(vi) {
	return [
		new THREE.Face3(0+vi, 1+vi, 2+vi),
		new THREE.Face3(3+vi, 4+vi, 5+vi),
		new THREE.Face3(0+vi, 2+vi, 3+vi),
		new THREE.Face3(0+vi, 3+vi, 5+vi),
	];
}

module.exports = {
	initScene: initScene,
	loadVariable: loadVariable
}