import './SubTitle.css';

const SubTitle = ({title, text}) => {
    return(
        <div id='subtitle-card'>
            <h1 id='subtitle-heading'>{title}</h1>
            <p id='subtitle-text'>{text}</p>
        </div>
    )
}

export default SubTitle;