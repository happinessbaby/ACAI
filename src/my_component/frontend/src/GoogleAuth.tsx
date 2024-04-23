import React, { useState, useEffect } from 'react';
import { googleLogout,  useGoogleLogin, TokenResponse, GoogleLogin} from '@react-oauth/google';
import axios from 'axios';

function GoogleSignin(props: any) {
    const [ user, setUser ] = useState<Omit<TokenResponse, "error" | "error_description" | "error_uri">>();
    const [ status, setStatus] = useState(true)
    // const [ profile, setProfile ] = useState(null);

    const login = useGoogleLogin({
        onSuccess: (codeResponse) => {setUser(codeResponse); console.log(codeResponse)},
        onError: (error) => console.log('Login Failed:', error)
    });


    useEffect(
        () => {
            const access_token = localStorage.getItem("accessTokenKey");
            axios
                .get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${access_token}`, {
                    headers: {
                        Authorization: `Bearer ${access_token}`,
                        Accept: 'application/json'
                    }
                })
                .then((res) => {
                    console.log("user already logged in")
                    props.signinCallback(access_token, res.data);
                    // setProfile(res.data);
                })
                .catch((err) =>  {setStatus(false); console.log("status set to false")});
            if (!status && user) {
                console.log(user.access_token);
                axios
                    .get(`https://www.googleapis.com/oauth2/v1/userinfo?access_token=${user.access_token}`, {
                        headers: {
                            Authorization: `Bearer ${user.access_token}`,
                            Accept: 'application/json'
                        }
                    })
                    .then((res) => {
                        console.log("logging in user")
                        props.signinCallback(user.access_token, res.data);
                        localStorage.setItem("accessTokenKey", user.access_token);
                        // setProfile(res.data);
                    })
                    .catch((err) => console.log(err));
            }
        },
        [ user ]
    );


    return (
        <div>
            <button onClick={() => login()}>Sign in with Google 🚀 </button>
        </div>
    )

    // log out function to log the user out of google and set the profile array to null
    // const logOut = () => {
    //     googleLogout();
    //     setProfile(null);
    // };

    // return (
    //     <div>
    //         <h2>React Google Login</h2>
    //         <br />
    //         <br />
    //         {profile ? (
    //             <div>
    //                 <img src={profile["picture"]} alt="user image" />
    //                 <h3>User Logged in</h3>
    //                 <p>Name: {profile["name"]}</p>
    //                 <p>Email Address: {profile["email"]}</p>
    //                 <br />
    //                 <br />
    //                 <button onClick={logOut}>Log out</button>
    //             </div>
    //         ) : (
    //             <button onClick={() => login()}>Sign in with Google 🚀 </button>
    //         )}
    //     </div>
    // );
}



function GoogleLogout() {
    // Revoke access token
    console.log("insie google log out")
    var access_token = localStorage.getItem("accessTokenKey");
    var revokeUrl = 'https://accounts.google.com/o/oauth2/revoke?token=' + access_token;

    // Send revoke request
    fetch(revokeUrl, {
        method: 'GET',
    })
    .then(response => {
        if (response.status === 200) {
            // Clear user session/storage
            /* clear user session/storage here */
            localStorage.removeItem("accessTokenKey");
            console.log('User logged out successfully.');
        } else {
            console.error('Failed to revoke access token.');
        }
    })
    .catch(error => {
        console.error('Error occurred while revoking access token:', error);
    });
    return <div></div>
}

export default {GoogleSignin, GoogleLogout};

