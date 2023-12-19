import React from "react"

function DisplaySession(props: any) {
    var lines = props.msgs.map(function(line:string, i:number) {
        // This is just an example - your return will pull information from `line`
        // Make sure to always pass a `key` prop when working with dynamic children: https://facebook.github.io/react/docs/multiple-components.html#dynamic-children
        return (
          <div key={i} onClick={() => props.onSelection(i)}>{line}</div>
        );
      });
    
      return (
        <div id='lineContainer'>
          {lines}
        </div>
      );

}

export default DisplaySession