import './SocialsLogo.css';

const SocialsLogo = ({link, image, alt}) => {
    return(
        <a href={link} id='socials-button'>
            <img id='social-button-img' src={image} alt={alt} />
        </a>
    )
}

export default SocialsLogo;