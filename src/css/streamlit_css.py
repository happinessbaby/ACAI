general_button = """<style>.element-container:has(.general-button) + div button {
            	box-shadow: -50px -50px 0px -50px #ffffff;
	background:linear-gradient(to bottom, #ffffff 5%, #f6f6f6 100%);
	background-color:#ffffff;
	border-radius:15px;
	border:1px solid #dcdcdc;
	display:inline-block;
	cursor:pointer;
	color:#0688fa;
	font-family:Arial;
	font-size:17px;
	padding:7px 25px;
	text-decoration:none;
	text-shadow:0px 1px 0px #ffffff;
            }
            .element-container:has(.general-button) + div button:hover {
                border:2px solid #dcdcdc;
            }
            .element-container:has(.general-button) + div button:active {
                position:relative;
                top:1px;
            } </style>
            """

primary_button =  """
            <style>
            button[kind="primary"] {
                background: none!important;
                border: none;
                padding: 0!important;
                color: black !important;
                text-decoration: none;
                cursor: pointer;
                border: none !important;
            }
            button[kind="primary"]:hover {
                text-decoration: none;
                color: blue !important;
            }
            button[kind="primary"]:focus {
                outline: none !important;
                box-shadow: none !important;
                color: blue !important;
            }
            </style>
            """

