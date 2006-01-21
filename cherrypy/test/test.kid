<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:py="http://purl.org/kid/ns#">
<head>
<title py:content="title">Title</title>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
</head>
<body>

${header}

<h1 py:content="title">There should be content</h1>

<ol py:if="title">
  <li py:for="line in lines">
  	<span py:replace="line"></span>
  </li>
</ol>

<dl>
  <span py:for="n, line in enumerate(lines)" py:omit="">
  <dt py:content="'Line %s' % n"></dt>
  <dd py:content="line"></dd>
  </span>
</dl>

<p py:content="mainloop"></p>
<p py:replace="'End of page'+title"></p>

</body>
</html>
