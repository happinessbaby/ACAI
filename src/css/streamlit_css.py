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
# ORANGE NO BORDER NO BACKGROUND
primary_button2 =  """
         <style>.element-container:has(.primary-button2) + div button {
            background: none;
            border: none;
            color: #ff9747;
            padding: 0;
            cursor: pointer;
            font-size: 12px; /* Adjust as needed */
            text-decoration: none;
            }
             .element-container:has(.primary-button2) + div button:hover {
               text-decoration: underline;
            }
            </style>
            """
primary_button="""
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
# LIGHT GREY NO BORDER NO BACKGROUND
primary_button3="""
            <style>
          .element-container:has(.primary-button3) + div button {
            background: none;
            border: none;
            color: #6C6C69;
            padding: 0;
            cursor: pointer;
            font-size: 6px; 
            text-decoration: none;
            }
            </style>
            """

primary_button4= """
         <style>.element-container:has(.primary-button4) + div button {
            background: none;
            border: none;
            color: #47ff5a;
            padding: 0;
            cursor: pointer;
            font-size: 12px; /* Adjust as needed */
            text-decoration: none;
            }
             .element-container:has(.primary-button4) + div button:hover {
               text-decoration: underline;
            }
            </style>
            """

tabs= """
<style>

	.stTabs [data-baseweb="tab-list"] {
		gap: 2px;
    }

	.stTabs [data-baseweb="tab"] {
		height: 50px;
        white-space: pre-wrap;
		background-color: #F0F2F6;
		border-radius: 4px 4px 0px 0px;
		gap: 1px;
		padding-top: 10px;
		padding-bottom: 10px;
    }

	.stTabs [aria-selected="true"] {
  		background-color: #FFFFFF;
	}

</style>"""

google_button = """
            <style>.element-container:has(#google-button-after) + div button {
                    cursor: pointer;
                    transition: background-color .3s, box-shadow .3s;
                        
                    padding: 16px 20px 16px 50px;
                    border: none;
                    border-radius: 3px;
                    box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 1px 1px rgba(0, 0, 0, .25);
                    
                    color: #757575;
                    font-size: 16px;
                    font-weight: 500;
                    font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,"Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
                    
                    background-image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTgiIGhlaWdodD0iMTgiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIj48cGF0aCBkPSJNMTcuNiA5LjJsLS4xLTEuOEg5djMuNGg0LjhDMTMuNiAxMiAxMyAxMyAxMiAxMy42djIuMmgzYTguOCA4LjggMCAwIDAgMi42LTYuNnoiIGZpbGw9IiM0Mjg1RjQiIGZpbGwtcnVsZT0ibm9uemVybyIvPjxwYXRoIGQ9Ik05IDE4YzIuNCAwIDQuNS0uOCA2LTIuMmwtMy0yLjJhNS40IDUuNCAwIDAgMS04LTIuOUgxVjEzYTkgOSAwIDAgMCA4IDV6IiBmaWxsPSIjMzRBODUzIiBmaWxsLXJ1bGU9Im5vbnplcm8iLz48cGF0aCBkPSJNNCAxMC43YTUuNCA1LjQgMCAwIDEgMC0zLjRWNUgxYTkgOSAwIDAgMCAwIDhsMy0yLjN6IiBmaWxsPSIjRkJCQzA1IiBmaWxsLXJ1bGU9Im5vbnplcm8iLz48cGF0aCBkPSJNOSAzLjZjMS4zIDAgMi41LjQgMy40IDEuM0wxNSAyLjNBOSA5IDAgMCAwIDEgNWwzIDIuNGE1LjQgNS40IDAgMCAxIDUtMy43eiIgZmlsbD0iI0VBNDMzNSIgZmlsbC1ydWxlPSJub256ZXJvIi8+PHBhdGggZD0iTTAgMGgxOHYxOEgweiIvPjwvZz48L3N2Zz4=);
                    background-color: white;
                    background-repeat: no-repeat;
                    background-position: 16px 50%;
                    }
                    .element-container:has(#google-button-after) + div button:hover { 
                        box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 2px 4px rgba(0, 0, 0, .25);
                    }
                </style>"""

linkedin_button="""
            <style>.element-container:has(#linkedin-button-after) + div button {
                    margin-top: -5px 
                    cursor: pointer;
                    transition: background-color .3s, box-shadow .3s;
                        
                    padding: 16px 20px 16px 50px;
                    border: none;
                    border-radius: 3px;
                    box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 1px 1px rgba(0, 0, 0, .25);
                    
                    color: #757575;
                    font-size: 16px;
                    font-weight: 500;
                    font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Oxygen,Ubuntu,Cantarell,"Fira Sans","Droid Sans","Helvetica Neue",sans-serif;
                    
                    background-image: url(data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiA/PjxzdmcgaGVpZ2h0PSI3MiIgdmlld0JveD0iMCAwIDcyIDcyIiB3aWR0aD0iNzIiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGcgZmlsbD0ibm9uZSIgZmlsbC1ydWxlPSJldmVub2RkIj48cGF0aCBkPSJNOCw3MiBMNjQsNzIgQzY4LjQxODI3OCw3MiA3Miw2OC40MTgyNzggNzIsNjQgTDcyLDggQzcyLDMuNTgxNzIyIDY4LjQxODI3OCwtOC4xMTYyNDUwMWUtMTYgNjQsMCBMOCwwIEMzLjU4MTcyMiw4LjExNjI0NTAxZS0xNiAtNS40MTA4MzAwMWUtMTYsMy41ODE3MjIgMCw4IEwwLDY0IEM1LjQxMDgzMDAxZS0xNiw2OC40MTgyNzggMy41ODE3MjIsNzIgOCw3MiBaIiBmaWxsPSIjMDA3RUJCIi8+PHBhdGggZD0iTTYyLDYyIEw1MS4zMTU2MjUsNjIgTDUxLjMxNTYyNSw0My44MDIxMTQ5IEM1MS4zMTU2MjUsMzguODEyNzU0MiA0OS40MTk3OTE3LDM2LjAyNDUzMjMgNDUuNDcwNzAzMSwzNi4wMjQ1MzIzIEM0MS4xNzQ2MDk0LDM2LjAyNDUzMjMgMzguOTMwMDc4MSwzOC45MjYxMTAzIDM4LjkzMDA3ODEsNDMuODAyMTE0OSBMMzguOTMwMDc4MSw2MiBMMjguNjMzMzMzMyw2MiBMMjguNjMzMzMzMywyNy4zMzMzMzMzIEwzOC45MzAwNzgxLDI3LjMzMzMzMzMgTDM4LjkzMDA3ODEsMzIuMDAyOTI4MyBDMzguOTMwMDc4MSwzMi4wMDI5MjgzIDQyLjAyNjA0MTcsMjYuMjc0MjE1MSA0OS4zODI1NTIxLDI2LjI3NDIxNTEgQzU2LjczNTY3NzEsMjYuMjc0MjE1MSA2MiwzMC43NjQ0NzA1IDYyLDQwLjA1MTIxMiBMNjIsNjIgWiBNMTYuMzQ5MzQ5LDIyLjc5NDAxMzMgQzEyLjg0MjA1NzMsMjIuNzk0MDEzMyAxMCwxOS45Mjk2NTY3IDEwLDE2LjM5NzAwNjcgQzEwLDEyLjg2NDM1NjYgMTIuODQyMDU3MywxMCAxNi4zNDkzNDksMTAgQzE5Ljg1NjY0MDYsMTAgMjIuNjk3MDA1MiwxMi44NjQzNTY2IDIyLjY5NzAwNTIsMTYuMzk3MDA2NyBDMjIuNjk3MDA1MiwxOS45Mjk2NTY3IDE5Ljg1NjY0MDYsMjIuNzk0MDEzMyAxNi4zNDkzNDksMjIuNzk0MDEzMyBaIE0xMS4wMzI1NTIxLDYyIEwyMS43Njk0MDEsNjIgTDIxLjc2OTQwMSwyNy4zMzMzMzMzIEwxMS4wMzI1NTIxLDI3LjMzMzMzMzMgTDExLjAzMjU1MjEsNjIgWiIgZmlsbD0iI0ZGRiIvPjwvZz48L3N2Zz4=);
                    background-color: white;
                    background-repeat: no-repeat;
                    background-position: 16px 50%;
                    background-size: 20px 20px; /* Adjust icon size here */
                    }
                    .element-container:has(#linkedin-button-after) + div button:hover { 
                        box-shadow: 0 -1px 0 rgba(0, 0, 0, .04), 0 2px 4px rgba(0, 0, 0, .25);
                    }
                </style>"""

included_skills_button = ["""
button {
  align-items: center;
  background-color: #FFE7E7;
  background-position: 0 0;
  border: 1px solid #FEE0E0;
  border-radius: 11px;
  box-sizing: border-box;
  color: #D33A2C;
  cursor: pointer;
  display: flex;
  font-size: 1rem;
  font-weight: 700;
  line-height: 33.4929px;
  list-style: outside url(https://www.smashingmagazine.com/images/bullet.svg) none;
  padding: 2px 12px;
  text-align: left;
  text-decoration: none;
  text-shadow: none;
  text-underline-offset: 1px;
  transition: border .2s ease-in-out,box-shadow .2s ease-in-out;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
  white-space: nowrap;
  word-break: break-word;
} """,
"""
button:active,
button:hover,
button:focus {
  outline: 0;
}""",
"""
button:active {
  background-color: #D33A2C;
  box-shadow: rgba(0, 0, 0, 0.12) 0 1px 3px 0 inset;
  color: #FFFFFF;
}""",
"""
button:hover {
  background-color: #FFE3E3;
  border-color: #FAA4A4;
}""",
"""
button:active:hover,
button:focus:hover,
button:focus {
  background-color: #D33A2C;
  box-shadow: rgba(0, 0, 0, 0.12) 0 1px 3px 0 inset;
  color: #FFFFFF;
}"""
]


suggested_skills_button = ["""
button {
  align-items: center;
  background-color:#E7FEE7;
  background-position: 0 0;
  border: 1px solid #D0FAD0;
  border-radius: 11px;
  box-sizing: border-box;
  color: #2C8A33;
  cursor: pointer;
  display: flex;
  font-size: 1rem;
  font-weight: 700;
  line-height: 33.4929px;
  list-style: outside url(https://www.smashingmagazine.com/images/bullet.svg) none;
  padding: 2px 12px;
  text-align: left;
  text-decoration: none;
  text-shadow: none;
  text-underline-offset: 1px;
  transition: border .2s ease-in-out,box-shadow .2s ease-in-out;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
  white-space: nowrap;
  word-break: break-word;
} """,
"""
button:active,
button:hover,
button:focus {
  outline: 0;
}""",
"""
button:active {
  background-color: #2C8A33;
  box-shadow: rgba(0, 0, 0, 0.12) 0 1px 3px 0 inset;
  color: #FFFFFF;
}""",
"""
button:hover {
  background-color: #DFFAD0;
  border-color: #A8FAA4;
}""",
"""
button:active:hover,
button:focus:hover,
button:focus {
  background-color: #2C8A33;
  box-shadow: rgba(0, 0, 0, 0.12) 0 1px 3px 0 inset;
  color: #FFFFFF;
}"""
]
# orange
new_upload_button = ["""button {
                                color: white;
                                background-color: #ff9747;
                            }""",
                            ]
# green
new_upload_button2 = ["""button {
                                color: white;
                                background-color: "#47ff5a";
                            }""",
                            ]