import './SigninComponent.css';
import { useState } from 'react';
import { Link } from 'react-router-dom';

const SigninComponent = () => {
    const [formData, setFormData] = useState({
        gmail: '',
        password: '',
    });
    const [showErrors, setShowErrors] = useState(false);
    const [errorMessages, setErrorMessages] = useState({
        gmail: '',
        password: ''
    });

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((prev) => ({ ...prev, [name]: value }));
        setShowErrors(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        let errors = {};
        let valid = true;

        if (!formData.gmail.includes('@') || formData.gmail.trim() === '') {
            errors.gmail = 'Enter a valid email';
            valid = false;
        }

        if (formData.password.length < 8) {
            errors.password = 'Password must be at least 8 characters';
            valid = false;
        }

        setErrorMessages(errors);
        setShowErrors(true);

        if (valid) {
            console.log("Form submitted with data:", formData);

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData),
                });

                const data = await response.json();

                if (response.ok) {
                    console.log('Login successful:', data);
                    // Handle login success (e.g., redirect)
                } else {
                    console.error('API Error:', data);
                }
            } catch (error) {
                console.error('Error during API call:', error);
            }

            setFormData({
                gmail: '',
                password: '',
            });
            setErrorMessages({});
        }
    };

    return (
        <div id="signup-div">
            <h1 id="signup-heading">Sign In</h1>
            <p id="login-link">Don't have an account? <Link to="/signup">Sign Up</Link></p>

            <form id="signup-form">
                <div className="input-wrapper" id="gmail-wrapper">
                    <label id='gmail-label' htmlFor="gmail-input">Gmail</label>
                    <input
                        type="email"
                        id="gmail-input"
                        name="gmail"
                        value={formData.gmail}
                        onChange={handleChange}
                        placeholder={errorMessages.gmail || 'Gmail'}
                        className={showErrors && errorMessages.gmail ? 'error' : ''}
                    />
                </div>

                <div className="input-wrapper" id="password-wrapper">
                    <label id='password-label' htmlFor="password-input">Password</label>
                    <input
                        type="password"
                        id="password-input"
                        name="password"
                        value={formData.password}
                        onChange={handleChange}
                        placeholder={errorMessages.password || 'Password'}
                        className={showErrors && errorMessages.password ? 'error' : ''}
                    />
                </div>

                <p id="terms-text">
                    By clicking 'Submit', you acknowledge that you have read and accept the{' '}
                    <a href="/terms" target="_blank" rel="noopener noreferrer">Terms of Service</a>{' '}
                    and{' '}
                    <a href="/privacy" target="_blank" rel="noopener noreferrer">Privacy Policy</a>.
                </p>

                <div className="input-wrapper" id="submit-wrapper">
                    <button type="submit" id="submit-button" onClick={handleSubmit}>Submit</button>
                </div>
            </form>
        </div>
    );
};

export default SigninComponent;
