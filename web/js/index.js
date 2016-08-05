'use strict';

var React = require('react');
var ReactDOM = require('react-dom');
var AutoComplete = require('react-autocomplete')
var $ = require("jquery");
var Button = require('react-bootstrap').Button;
var Grid = require('react-bootstrap').Grid;
var Row = require('react-bootstrap').Row;
var Col = require('react-bootstrap').Col;
var Panel = require('react-bootstrap').Panel;
var Form = require('react-bootstrap').Form;
var FormGroup = require('react-bootstrap').FormGroup;
var ControlLabel = require('react-bootstrap').ControlLabel;
var EarthScene = require('./globe.js').EarthScene;

var runs = [
	{name: 'i-54e4fec1'},
	{name: 'i-10bca685'},
	{name: 'i-759d7be1'},
	{name: 'i-26ae4ab2'},
	{name: 'i-d4c62640'}
]

const PROVIDER_URI = 'https://4vesdtyv82.execute-api.us-west-2.amazonaws.com/dev';

var styles = {
  item: {
    padding: '4px 8px',
    cursor: 'default',
    zIndex: 1000000
  },

  highlightedItem: {
    color: 'white',
    background: 'hsl(200, 50%, 50%)',
    padding: '4px 8px',
    cursor: 'default',
    zIndex: 1000000
  },

  menu: {
    border: 'solid 1px #ccc'
  }
}

var menuStyle = {
        borderRadius: '3px',
        boxShadow: '0 2px 12px rgba(0, 0, 0, 0.1)',
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '2px 0',
        fontSize: '90%',
        position: 'fixed',
        overflow: 'auto',
        zIndex: 1000,
        maxHeight: '50%'
    }

var inputStyle = {
	fontSize: '14px',
	marginTop: '4px'
}

function matchToTerm (field) {
	return function(item, value) {
		return item[field].toLowerCase().indexOf(value.toLowerCase()) !== -1 		
	}
}

var ControlPanel = React.createClass({
	render: function() {
		return (<div/>)
	}
})

var ViewPanel = React.createClass({
	render: function() {
		return (
			<div 
				id="scene-container" 
				style={{ position: "fixed", left: "0px", top: "0px", zIndex: -1}}
			/>
		)
	},
	componentDidMount: function() {
		console.log('Loading geo data');
		$.getJSON("./data/geodesic_data.json", function(json) {
			console.log('done loading geo data');
			new EarthScene(json);
		});		
	}
})

var SearchBar = React.createClass({
	getInitialState: function() {
		return {
			searchText: ''
		}
	},
	onRunSelect: function(runId) {
		this.setState({ searchText: runId });
		this.props.loadRun(runId);
	},
	render: function() {
		return (
			<FormGroup>
			<Col sm={2} componentClass={ControlLabel}>Run</Col>
			<Col sm={2}><AutoComplete 
				value={this.state.searchText}
				items={this.props.getItems}
				inputProps={{ id: "run-search", style: inputStyle}}
				menuStyle={menuStyle}
				getItemValue={(item) => item.InstanceId}
				shouldItemRender={matchToTerm('InstanceId')}
				onChange={(event, value) => this.setState( {  searchText: value } )}
				onSelect={this.onRunSelect}
				renderItem={(item, isHighlighted) => (
		            <div
		              style={isHighlighted ? styles.highlightedItem : styles.item}
		              key={item.InstanceId}
		            >{item.InstanceId}: {item.CreatedTime}</div>
          			)}			
				/></Col>
			</FormGroup>
		)
	}
})

var TimeSelector = React.createClass({
	render: function() {
		return (<div/>)
	}
})

var OutputVariablePicker = React.createClass({
	getInitialState: function() {
		return {
			searchText: ''
		}
	},
	onVariableSelect: function(item) {
		this.setState({ searchText: item.varName });
		this.props.variableSelected(item)
	},
	render: function() {
		return (
			<FormGroup>
			<Col sm={2} componentClass={ControlLabel}>Var.</Col>
			<Col sm={2}><AutoComplete
				value={this.state.searchText}
				items={this.props.getItems}
				inputProps={{ id: "variable-search", style: inputStyle, disabled: this.props.disabled }}
				menuStyle={menuStyle}
				getItemValue={(item) => item}
				shouldItemRender={matchToTerm('varName')}
				onChange={(event, value) => this.setState({ searchText: value })}
				onSelect={this.onVariableSelect}
				renderItem={(item, isHighlighted) => (
		            <div
		              style={isHighlighted ? styles.highlightedItem : styles.item}
		              key={item.model+'_'+item.varName}
		            >{item.model} - {item.varName}</div>
          			)}			
			/></Col>
			</FormGroup>
		)
	}
})

var NavigatorPanel = React.createClass({
	getInitialState: function() {
		return {
			runs: [],
			variables: [],
			loading: false
		}
	},
	componentDidMount: function() {
		$.ajax({
			url: PROVIDER_URI+'/runs',
			dataType: 'json',
			cache: false,
			success: function(data) {
				// console.log(data);
				data.sort((a, b) => a.CreatedTime < b.CreatedTime ? 1: -1);
				this.setState({ runs: data });
			}.bind(this),
			error: function(xhr, status, error) {
				console.error('url', status, error); 
			}.bind(this)
		})
	},
	setLoading: function(isLoading) {
		this.setState({ loading: isLoading });
	},
	loadRun: function(runId) {
		console.log('Loading '+runId);
		this.setState({ variables: [] });
		this.setLoading(true);
		$.ajax({
			url: PROVIDER_URI+'/run/'+runId,
			dataType: 'json',
			cache: false,
			success: function(data) {
				var variables = $.map(
					data.output, 
					function(v, i) { return {varName: v[1], model: v[0], key: v[2]} }
				);
				this.setState({ variables: variables });
				this.setLoading(false);
			}.bind(this),
			error: function(xhr, status, error) {
				console.error('url', status, error); 
				this.setLoading(false);
			}.bind(this)			
		})
	},

	render: function() {
		return (
			<Panel className="navigatorPanel" style={{padding:"0px"}}>
				<Form horizontal>
					<FormGroup><Col sm={3}><h1>Earther</h1></Col></FormGroup>
					<SearchBar 
						getItems={this.state.runs}
						loadRun={this.loadRun}
					/>
					
					<OutputVariablePicker 
						getItems={this.state.variables}
					/>
					<FormGroup>
						<Col smOffset={2} sm={2}>
							<Button bsSize="small" bsStyle="primary">Engage!</Button>
						</Col>
					</FormGroup>
				</Form>
			</Panel>
		);
	}
})

var MainPanel = React.createClass({
	render: function() {
		return (
			<div className="mainPanel"  style={{width: "20%"}}>
				<NavigatorPanel />
				<ControlPanel />
				<ViewPanel />
			</div>
		);
	}
});

ReactDOM.render(
	<MainPanel />,
	document.getElementById('content')
);
